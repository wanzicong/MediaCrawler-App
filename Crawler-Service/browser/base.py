# -*- coding: utf-8 -*-
"""
浏览器抽象接口

爬虫只依赖此接口，不直接 import Playwright。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class BrowserLaunchOptions:
    """浏览器启动配置"""
    headless: bool = False
    proxy: Optional[Dict[str, str]] = None
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    args: List[str] = field(default_factory=list)
    cdp_port: Optional[int] = None
    connect_existing: bool = False
    user_data_dir: Optional[str] = None
    timeout: int = 60000
    cookies: List[Dict[str, str]] = field(default_factory=list)


@runtime_checkable
class BrowserPage(Protocol):
    """浏览器页面接口"""
    async def goto(self, url: str, **kwargs) -> Any: ...
    async def wait_for_selector(self, selector: str, **kwargs) -> Any: ...
    async def wait_for_load_state(self, state: str = "load") -> None: ...
    async def content(self) -> str: ...
    async def evaluate(self, expression: str, *args) -> Any: ...
    async def click(self, selector: str, **kwargs) -> None: ...
    async def fill(self, selector: str, value: str, **kwargs) -> None: ...
    @property
    def url(self) -> str: ...
    async def close(self) -> None: ...
    async def screenshot(self, **kwargs) -> bytes: ...
    async def query_selector_all(self, selector: str) -> List[Any]: ...


@runtime_checkable
class BrowserContext(Protocol):
    """浏览器上下文接口"""
    async def new_page(self) -> BrowserPage: ...
    async def add_cookies(self, cookies: List[Dict[str, Any]]) -> None: ...
    async def cookies(self) -> List[Dict[str, Any]]: ...
    async def close(self) -> None: ...


class AbstractBrowser(ABC):
    """
    浏览器抽象基类

    所有浏览器实现（Playwright、Selenium 等）需实现此接口。
    爬虫通过此接口操作浏览器，不直接依赖任何具体实现。
    """

    @abstractmethod
    async def launch(self, options: BrowserLaunchOptions) -> BrowserContext:
        """启动浏览器并返回上下文"""
        ...

    @abstractmethod
    async def launch_cdp(
        self, options: BrowserLaunchOptions, cdp_url: Optional[str] = None,
    ) -> BrowserContext:
        """通过 CDP 协议连接浏览器"""
        ...

    @abstractmethod
    async def create_context(self, **kwargs) -> BrowserContext:
        """创建新的浏览器上下文"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭浏览器"""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """检查浏览器是否仍连接"""
        ...

    @abstractmethod
    async def get_page_content(self, page: BrowserPage) -> str:
        """获取页面 HTML"""
        ...

    @abstractmethod
    async def execute_script(self, page: BrowserPage, script: str) -> Any:
        """执行 JavaScript"""
        ...

    @abstractmethod
    async def take_screenshot(self, page: BrowserPage, path: Optional[str] = None) -> bytes:
        """截图"""
        ...

    @abstractmethod
    async def intercept_request(self, page: BrowserPage, url_pattern: str, handler) -> None:
        """拦截网络请求"""
        ...

    @abstractmethod
    async def get_requests(self, page: BrowserPage, url_pattern: str) -> List[Any]:
        """获取匹配的请求记录"""
        ...

    @abstractmethod
    async def wait_for_response(
        self, page: BrowserPage, url_pattern: str, timeout: int = 30000,
    ) -> Any:
        """等待特定请求的响应"""
        ...

