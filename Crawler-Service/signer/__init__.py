# -*- coding: utf-8 -*-
"""
签名服务客户端

爬虫通过此客户端调用签名微服务，而非内嵌签名逻辑。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

SIGNER_URL = os.getenv("SIGNER_SERVICE_URL", "http://127.0.0.1:8082")
SIGNER_FAIL_FAST = os.getenv("SIGNER_FAIL_FAST", "false").lower() in ("1", "true", "yes")


class SignerClient:
    """签名服务 HTTP 客户端"""

    def __init__(self, base_url: str = SIGNER_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def sign(
        self,
        platform: str,
        sign_type: str = "api",
        url: str = "",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """调用签名服务获取签名"""
        payload = {
            "platform": platform,
            "sign_type": sign_type,
            "url": url,
            "params": params or {},
            "headers": headers or {},
            "cookies": cookies or {},
            "extra": extra or {},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/sign", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError as e:
            if SIGNER_FAIL_FAST:
                raise RuntimeError(f"Signer service unavailable at {self.base_url}") from e
            print(f"[SignerClient] 签名服务不可用，降级为空签名 ({platform}/{sign_type})")
            return {
                "platform": platform,
                "sign_type": sign_type,
                "url": url,
                "params": params or {},
                "headers": headers or {},
                "cookies": cookies or {},
                "extra": {},
                "degraded": True,
            }
        except Exception as e:
            if SIGNER_FAIL_FAST:
                raise
            print(f"[SignerClient] 签名失败 ({platform}/{sign_type}): {e}")
            return {
                "platform": platform,
                "sign_type": sign_type,
                "url": url,
                "params": params or {},
                "headers": headers or {},
                "cookies": cookies or {},
                "error": str(e),
                "degraded": True,
            }

    async def sign_batch(self, requests: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """批量签名"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                resp = await client.post(f"{self.base_url}/api/sign/batch", json=requests)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            print(f"[SignerClient] 批量签名失败: {e}")
            return requests

    async def health(self) -> bool:
        """检查签名服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/health")
                return resp.status_code == 200
        except Exception:
            return False


# 全局客户端实例
signer = SignerClient()
