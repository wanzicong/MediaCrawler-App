# -*- coding: utf-8 -*-
"""
签名服务基础接口和签名器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SignRequest:
    """签名请求"""
    platform: str
    sign_type: str  # e.g. "api", "web", "search", "detail"
    url: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignResult:
    """签名结果"""
    platform: str
    sign_type: str
    url: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


class AbstractSigner(ABC):
    """签名器抽象基类"""

    PLATFORM: str = "unknown"

    @abstractmethod
    async def sign(self, request: SignRequest) -> SignResult:
        """对请求进行签名"""
        ...

    @abstractmethod
    async def validate(self, result: SignResult) -> bool:
        """验证签名是否有效"""
        ...

    @abstractmethod
    def cache_key(self, request: SignRequest) -> str:
        """生成缓存键"""
        ...

