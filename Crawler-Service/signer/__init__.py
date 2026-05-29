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
        except httpx.ConnectError:
            # 签名服务不可用时返回空签名 (降级模式)
            return {
                "platform": platform,
                "sign_type": sign_type,
                "url": url,
                "params": params or {},
                "headers": headers or {},
                "cookies": cookies or {},
                "extra": {},
            }
        except Exception as e:
            print(f"[SignerClient] 签名失败 ({platform}/{sign_type}): {e}")
            return {
                "platform": platform,
                "sign_type": sign_type,
                "url": url,
                "params": params or {},
                "headers": headers or {},
                "cookies": cookies or {},
                "error": str(e),
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
