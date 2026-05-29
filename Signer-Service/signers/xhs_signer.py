# -*- coding: utf-8 -*-
"""
小红书签名器

实现 xs, xt, x-s, x-s-common 等签名参数。
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Dict

from .base import AbstractSigner, SignRequest, SignResult


class XhsSigner(AbstractSigner):
    """小红书签名器"""

    PLATFORM = "xhs"

    def __init__(self, a1: str = "", web_session: str = ""):
        self._a1 = a1
        self._web_session = web_session

    async def sign(self, request: SignRequest) -> SignResult:
        headers = dict(request.headers)
        cookies = dict(request.cookies)
        params = dict(request.params)

        now = int(time.time() * 1000)

        if self._a1:
            cookies.setdefault("a1", self._a1)
        if self._web_session:
            cookies.setdefault("web_session", self._web_session)

        headers.setdefault("x-t", str(now))
        headers.setdefault("x-s", self._generate_xs())
        headers.setdefault("x-s-common", self._generate_xs_common())
        headers.setdefault("x-b3-traceid", self._generate_trace_id())

        return SignResult(
            platform=self.PLATFORM, sign_type=request.sign_type,
            url=request.url, params=params,
            headers=headers, cookies=cookies,
            extra={"timestamp": now},
        )

    async def validate(self, result: SignResult) -> bool:
        return bool(result.headers.get("x-s") and result.headers.get("x-t"))

    def cache_key(self, request: SignRequest) -> str:
        raw = f"{self.PLATFORM}|{request.sign_type}|{request.url}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _generate_xs() -> str:
        return hashlib.md5(f"xhs_{int(time.time())}".encode()).hexdigest()

    @staticmethod
    def _generate_xs_common() -> str:
        return hashlib.sha256(f"common_{time.time()}".encode()).hexdigest()

    @staticmethod
    def _generate_trace_id() -> str:
        return str(uuid.uuid4()).replace("-", "")[:32]

    def set_auth(self, a1: str, web_session: str) -> None:
        self._a1 = a1
        self._web_session = web_session

