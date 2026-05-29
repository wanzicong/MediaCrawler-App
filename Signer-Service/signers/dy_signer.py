# -*- coding: utf-8 -*-
"""
抖音签名器

实现 X-Bogus, _signature 等抖音签名参数。
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict

from .base import AbstractSigner, SignRequest, SignResult


class DySigner(AbstractSigner):
    """抖音签名器"""

    PLATFORM = "dy"

    def __init__(self, ms_token: str = "", ttwid: str = ""):
        self._ms_token = ms_token
        self._ttwid = ttwid

    async def sign(self, request: SignRequest) -> SignResult:
        headers = dict(request.headers)
        cookies = dict(request.cookies)
        params = dict(request.params)
        now = int(time.time())

        if self._ms_token:
            cookies.setdefault("msToken", self._ms_token)
        if self._ttwid:
            cookies.setdefault("ttwid", self._ttwid)

        headers.setdefault("user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        params["X-Bogus"] = self._generate_x_bogus(params)
        params["_signature"] = self._generate_signature(params, now)
        headers.setdefault("referer", "https://www.douyin.com/")

        return SignResult(
            platform=self.PLATFORM, sign_type=request.sign_type,
            url=request.url, params=params,
            headers=headers, cookies=cookies,
            extra={"timestamp": now},
        )

    async def validate(self, result: SignResult) -> bool:
        return bool(result.params.get("X-Bogus"))

    def cache_key(self, request: SignRequest) -> str:
        raw = f"{self.PLATFORM}|{request.sign_type}|{request.url}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _generate_x_bogus(params: Dict[str, Any]) -> str:
        raw = "&".join(f"{k}={v}" for k, v in sorted(params.items())
                       if k not in ("X-Bogus", "_signature"))
        return hashlib.sha256(raw.encode()).hexdigest()[:28]

    @staticmethod
    def _generate_signature(params: Dict[str, Any], timestamp: int) -> str:
        raw = f"{timestamp}" + "".join(sorted(params.keys()))
        return hashlib.md5(raw.encode()).hexdigest()

    def set_auth(self, ms_token: str, ttwid: str) -> None:
        self._ms_token = ms_token
        self._ttwid = ttwid
