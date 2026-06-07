# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/base/base_crawler.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from playwright.async_api import BrowserContext, BrowserType, Playwright

from tools import utils


class AbstractCrawler(ABC):
    """
    抽象爬虫基类 — 统一管理浏览器生命周期。

    子类只需实现 start() / search() 等业务方法，浏览器启动和清理由基类统一处理。

    浏览器模式 (由 config.BROWSER_MODE 控制):
      - "auto" (默认):   优先使用 Browser-Service 远程浏览器池，不可用时回退本地 CDP
      - "remote":        强制使用 Browser-Service（无 Browser-Service 则报错）
      - "local":         强制使用本地 CDP 模式（不依赖 Browser-Service）

    Usage (子类 start 方法):
        async def start(self):
            async with async_playwright() as playwright:
                if config.ENABLE_CDP_MODE and not headless:
                    self.browser_context = await self.launch_browser_with_cdp(
                        playwright, proxy, user_agent, headless=False)
                else:
                    chromium = playwright.chromium
                    self.browser_context = await self.launch_browser(
                        chromium, proxy, user_agent, headless=True)
                # ... 爬取逻辑 ...
            # async with 退出后 playwright 自动停止
    """

    # ------------------------------------------------------------------
    # 构造器
    # ------------------------------------------------------------------

    def __init__(self):
        self.browser_context: Optional[BrowserContext] = None

    # ==================== 抽象方法（子类必须实现） ====================

    @abstractmethod
    async def start(self):
        """启动爬虫（子类实现）"""
        pass

    @abstractmethod
    async def search(self):
        """搜索（子类实现）"""
        pass

    # ==================== 浏览器管理（基类统一实现） ====================

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        标准 Playwright 模式启动浏览器。

        用于 headless 场景或 CDP 不可用时的回退方案。
        子类可以覆盖此方法实现平台特有逻辑（如贴吧的反检测注入）。

        Args:
            chromium: Playwright chromium BrowserType
            playwright_proxy: 代理配置字典 {"server": "http://..."}
            user_agent: 自定义 User-Agent
            headless: 是否无头模式

        Returns:
            BrowserContext 对象
        """
        import config

        utils.logger.info(
            f"[{self.__class__.__name__}.launch_browser] "
            f"Begin create browser context (headless={headless}) ..."
        )

        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                os.getcwd(), "browser_data",
                config.USER_DATA_DIR % config.PLATFORM  # type: ignore
            )
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(
                headless=headless, proxy=playwright_proxy  # type: ignore
            )
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        统一 CDP 模式浏览器启动 — 优先使用 Browser-Service，回退到本地 CDP。

        工作流程:
          1. 读取 config.BROWSER_MODE 决定策略
          2. "remote" / "auto": 尝试 BrowserServiceClient
          3. "local" / fallback: 使用本地 CDPBrowserManager
          4. 最终回退: launch_browser() 标准 Playwright 模式

        子类可以覆盖此方法实现平台特有逻辑。

        Args:
            playwright: Playwright 实例
            playwright_proxy: 代理配置
            user_agent: 自定义 User-Agent
            headless: 是否无头模式

        Returns:
            BrowserContext 对象

        Raises:
            RuntimeError: BROWSER_MODE=remote 且 Browser-Service 不可用时
        """
        import config

        mode = getattr(config, "BROWSER_MODE", "auto")
        # 存到实例属性供后续查询
        self._browser_mode = mode

        utils.logger.info(
            f"[{self.__class__.__name__}.launch_browser_with_cdp] "
            f"Browser mode: {mode}, headless={headless}"
        )

        # 策略 1: 尝试 Browser-Service（remote / auto 模式）
        if mode in ("remote", "auto"):
            try:
                browser_context = await self._launch_via_browser_service(
                    playwright=playwright,
                    playwright_proxy=playwright_proxy,
                    user_agent=user_agent,
                    headless=headless,
                )
                if browser_context is not None:
                    return browser_context
            except Exception as e:
                if mode == "remote":
                    # remote 模式下不允许回退
                    raise RuntimeError(
                        f"Browser-Service unavailable and BROWSER_MODE=remote: {e}"
                    ) from e
                utils.logger.warning(
                    f"[{self.__class__.__name__}] Browser-Service failed ({e}), "
                    f"falling back to local CDP..."
                )

        # remote 模式下 Browser-Service 不可用（返回 None 或不可达）也必须报错
        if mode == "remote":
            raise RuntimeError(
                "Browser-Service unavailable and BROWSER_MODE=remote. "
                "Please ensure Browser-Service is running or set BROWSER_MODE=auto."
            )

        # 策略 2: 本地 CDP 模式（local 或 auto 回退）
        return await self._launch_via_local_cdp(
            playwright=playwright,
            playwright_proxy=playwright_proxy,
            user_agent=user_agent,
            headless=headless,
        )

    # ==================== 内部辅助方法 ====================

    async def _launch_via_browser_service(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool,
    ) -> Optional[BrowserContext]:
        """
        通过 Browser-Service 远程启动浏览器。

        Returns:
            BrowserContext 如果成功, None 如果 Browser-Service 不可用
        """
        try:
            from tools.browser_service_client import BrowserServiceClient
        except ImportError:
            utils.logger.warning(
                "[AbstractCrawler] BrowserServiceClient not available, skip remote mode"
            )
            return None

        import config

        client = BrowserServiceClient()

        # 健康检查：确认 Browser-Service 可达
        if not await client._check_availability():
            utils.logger.info(
                "[AbstractCrawler] Browser-Service not reachable, skip remote mode"
            )
            return None

        platform = getattr(config, "PLATFORM", "unknown")

        browser_context = await client.launch_and_connect(
            playwright=playwright,
            playwright_proxy=playwright_proxy,
            user_agent=user_agent,
            headless=headless,
            platform=platform,
        )

        # 保存客户端引用用于后续清理
        self._browser_client = client

        # 显示浏览器信息
        browser_info = await client.get_browser_info()
        utils.logger.info(
            f"[{self.__class__.__name__}] Remote browser info: {browser_info}"
        )

        return browser_context

    async def _launch_via_local_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool,
    ) -> BrowserContext:
        """
        通过本地 CDPBrowserManager 启动浏览器。

        如果本地 CDP 启动失败，自动回退到标准 Playwright 模式。

        Returns:
            BrowserContext 对象

        Raises:
            RuntimeError: 无法导入 CDPBrowserManager 时
        """
        try:
            from tools.cdp_browser import CDPBrowserManager
        except ImportError as e:
            raise RuntimeError(
                "Cannot import CDPBrowserManager for local CDP mode. "
                "Please ensure Crawler-Service is properly installed."
            ) from e

        try:
            manager = CDPBrowserManager()
            browser_context = await manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # 保存 cdp_manager 引用（向后兼容）
            self.cdp_manager = manager

            # 显示浏览器信息
            browser_info = await manager.get_browser_info()
            utils.logger.info(
                f"[{self.__class__.__name__}] Local CDP browser info: {browser_info}"
            )

            return browser_context

        except Exception as e:
            utils.logger.error(
                f"[{self.__class__.__name__}] Local CDP launch failed, "
                f"falling back to standard mode: {e}"
            )
            chromium = playwright.chromium
            return await self.launch_browser(
                chromium, playwright_proxy, user_agent, headless
            )

    # ==================== 清理 ====================

    async def close(self):
        """
        统一浏览器清理。

        清理顺序:
          1. Browser-Service 远程模式 → 通过 BrowserServiceClient.cleanup()
          2. 本地 CDP 模式 → 通过 cdp_manager.cleanup()
          3. 标准 Playwright 模式 → 直接关闭 browser_context

        防御性设计: 兼容子类未调用 super().__init__() 的情况，
        使用 getattr 安全访问实例属性。
        """
        client = getattr(self, "_browser_client", None)
        manager = getattr(self, "cdp_manager", None)
        context = getattr(self, "browser_context", None)

        # 1. 远程 Browser-Service 模式
        if client is not None:
            try:
                await client.cleanup()
                utils.logger.info(
                    f"[{self.__class__.__name__}.close] "
                    "Browser-Service client cleaned up"
                )
            except Exception as e:
                utils.logger.warning(
                    f"[{self.__class__.__name__}.close] "
                    f"Error cleaning Browser-Service client: {e}"
                )
            finally:
                self._browser_client = None
                self.browser_context = None
            # 注意: 不提前 return，继续清理可能残留的 cdp_manager

        # 2. 本地 CDP 模式
        if manager is not None:
            try:
                await manager.cleanup()
                utils.logger.info(
                    f"[{self.__class__.__name__}.close] "
                    "CDP manager cleaned up"
                )
            except Exception as e:
                utils.logger.warning(
                    f"[{self.__class__.__name__}.close] "
                    f"Error cleaning CDP manager: {e}"
                )
            finally:
                self.cdp_manager = None
                self.browser_context = None

        # 3. 标准 Playwright 模式 / 残留 browser_context
        if context is not None:
            try:
                await context.close()
                utils.logger.info(
                    f"[{self.__class__.__name__}.close] "
                    "Browser context closed"
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    utils.logger.warning(
                        f"[{self.__class__.__name__}.close] "
                        f"Error closing browser context: {e}"
                    )
            finally:
                self.browser_context = None

    # ==================== 辅助方法 ====================

    def is_browser_connected(self) -> bool:
        """
        检查浏览器是否仍然连接。

        按优先级检查: BrowserServiceClient → CDPBrowserManager → BrowserContext
        """
        # 1. 检查 BrowserServiceClient
        client = getattr(self, "_browser_client", None)
        if client is not None:
            return client.is_connected()

        # 2. 检查本地 CDPBrowserManager
        manager = getattr(self, "cdp_manager", None)
        if manager is not None:
            return manager.is_connected()

        # 3. 检查标准 Playwright BrowserContext
        context = getattr(self, "browser_context", None)
        if context is not None:
            try:
                # BrowserContext 本身没有 is_connected()，检查 pages 是否可访问
                _pages = context.pages
                return True
            except Exception:
                return False

        return False

    async def add_stealth_script(self, script_path: str = "libs/stealth.min.js"):
        """
        注入反检测脚本。

        按优先级注入:
          1. BrowserServiceClient (远程模式)
          2. CDPBrowserManager (本地 CDP 模式)
          3. BrowserContext (标准 Playwright 模式)
        """
        client = getattr(self, "_browser_client", None)
        manager = getattr(self, "cdp_manager", None)
        context = getattr(self, "browser_context", None)

        if client is not None:
            await client.add_stealth_script(script_path)
        elif manager is not None:
            await manager.add_stealth_script(script_path)
        elif context is not None and os.path.exists(script_path):
            await context.add_init_script(path=script_path)
            utils.logger.info(f"[AbstractCrawler] Added stealth script: {script_path}")

    @property
    def browser_mode(self) -> str:
        """返回当前浏览器模式（auto / remote / local）。"""
        return getattr(self, "_browser_mode", "auto")


class AbstractLogin(ABC):

    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def login_by_qrcode(self):
        pass

    @abstractmethod
    async def login_by_mobile(self):
        pass

    @abstractmethod
    async def login_by_cookies(self):
        pass


class AbstractStore(ABC):

    @abstractmethod
    async def store_content(self, content_item: Dict):
        pass

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        pass

    # TODO support all platform
    # only xhs is supported, so @abstractmethod is commented
    @abstractmethod
    async def store_creator(self, creator: Dict):
        pass


class AbstractStoreImage(ABC):
    # TODO: support all platform
    # only weibo is supported
    async def store_image(self, image_content_item: Dict):
        pass


class AbstractStoreVideo(ABC):
    # TODO: support all platform
    # only weibo is supported
    async def store_video(self, video_content_item: Dict):
        pass


class AbstractApiClient(ABC):

    @abstractmethod
    async def request(self, method, url, **kwargs):
        pass

    @abstractmethod
    async def update_cookies(self, browser_context: BrowserContext):
        pass
