# -*- coding: utf-8 -*-
"""
Playwright 浏览器实现

包装 Playwright API，实现 AbstractBrowser 接口。
支持标准模式和 CDP 模式。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from playwright.async_api import (
    Browser as PWBrowser,
    BrowserContext as PWBrowserContext,
    Page as PWPage,
    Playwright,
    async_playwright,
)

from .base import AbstractBrowser, BrowserContext, BrowserLaunchOptions, BrowserPage


class PlaywrightBrowser(AbstractBrowser):
    """Playwright 浏览器实现"""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[PWBrowser] = None
        self._context: Optional[PWBrowserContext] = None

    async def launch(self, options: BrowserLaunchOptions) -> BrowserContext:
        self._playwright = await async_playwright().start()

        launch_args = options.args or [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

        launch_kwargs: Dict[str, Any] = {
            "headless": options.headless,
            "args": launch_args,
        }

        if options.proxy:
            launch_kwargs["proxy"] = options.proxy

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

        ctx_kwargs: Dict[str, Any] = {"viewport": options.viewport}
        if options.user_agent:
            ctx_kwargs["user_agent"] = options.user_agent

        self._context = await self._browser.new_context(**ctx_kwargs)

        if options.cookies:
            await self._context.add_cookies(options.cookies)

        return self._context

    async def launch_cdp(
        self, options: BrowserLaunchOptions, cdp_url: Optional[str] = None,
    ) -> BrowserContext:
        self._playwright = await async_playwright().start()

        if cdp_url:
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        elif options.cdp_port:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{options.cdp_port}"
            )
        else:
            launch_args = options.args or [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
            port = options.cdp_port or 9222
            launch_args.append(f"--remote-debugging-port={port}")

            self._browser = await self._playwright.chromium.launch(
                headless=options.headless,
                args=launch_args,
            )

        ctx_kwargs: Dict[str, Any] = {"viewport": options.viewport}
        if options.user_agent:
            ctx_kwargs["user_agent"] = options.user_agent
        if options.proxy:
            ctx_kwargs["proxy"] = options.proxy

        self._context = await self._browser.new_context(**ctx_kwargs)

        if options.cookies:
            await self._context.add_cookies(options.cookies)

        return self._context

    async def create_context(self, **kwargs) -> BrowserContext:
        if self._browser:
            return await self._browser.new_context(**kwargs)
        raise RuntimeError("Browser not launched")

    async def close(self) -> None:
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def is_connected(self) -> bool:
        if self._browser:
            try:
                return self._browser.is_connected()
            except Exception:
                return False
        return False

    async def get_page_content(self, page: BrowserPage) -> str:
        return await page.content()

    async def execute_script(self, page: BrowserPage, script: str) -> Any:
        return await page.evaluate(script)

    async def take_screenshot(self, page: BrowserPage, path: Optional[str] = None) -> bytes:
        kwargs = {}
        if path:
            kwargs["path"] = path
        return await page.screenshot(**kwargs)

    async def intercept_request(
        self, page: BrowserPage, url_pattern: str, handler,
    ) -> None:
        async def _handle_route(route):
            await handler(route, route.request)
        await page.route(url_pattern, _handle_route)

    async def get_requests(self, page: BrowserPage, url_pattern: str) -> List[Any]:
        return []

    async def wait_for_response(
        self, page: BrowserPage, url_pattern: str, timeout: int = 30000,
    ) -> Any:
        return await page.wait_for_response(url_pattern, timeout=timeout)

    async def new_page(self) -> BrowserPage:
        if not self._context:
            raise RuntimeError("Context not created. Call launch() first.")
        return await self._context.new_page()

    @property
    def context(self) -> Optional[PWBrowserContext]:
        return self._context

    @property
    def browser(self) -> Optional[PWBrowser]:
        return self._browser

