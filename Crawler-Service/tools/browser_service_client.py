# -*- coding: utf-8 -*-
"""
Browser-Service 客户端

替代 CDPBrowserManager, 通过 HTTP REST API 与 Browser-Service 通信,
使用 Playwright 的 connect_over_cdp 连接远程浏览器实例。

功能:
  - launch_and_connect: 从 Browser-Service 获取浏览器实例, 通过 CDP 连接
  - cleanup: 通知 Browser-Service 销毁实例
  - health_check: 检查远程浏览器实例健康状态
  - is_connected: 检查本地与远程浏览器的连接状态
  - fallback: Browser-Service 不可用时回退到本地 CDPBrowserManager

Usage:
    client = BrowserServiceClient(base_url="http://browser-service:9500")
    browser_context = await client.launch_and_connect(
        playwright=playwright,
        proxy={"server": "http://proxy:8080"},
        user_agent="Mozilla/5.0 ...",
        headless=True,
    )
    # ... use browser_context ...
    await client.cleanup()
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from tools import utils

logger = logging.getLogger("browser_service_client")


class BrowserServiceClient:
    """
    通过 HTTP + WebSocket 与 Browser-Service 通信的客户端。

    替代 CDPBrowserManager:
      - 从 Browser-Service 池中申请浏览器实例
      - 通过 Playwright 的 connect_over_cdp(ws_url) 连接
      - 使用完毕后归还/销毁实例

    自动 Fallback:
      如果 Browser-Service 不可用 (连接超时/拒绝), 自动回退到
      本地 CDPBrowserManager, 保持兼容性。
    """

    # ---- 配置 ----

    # 默认 Browser-Service 地址, 可通过环境变量 BROWSER_SERVICE_URL 覆盖
    DEFAULT_BASE_URL: str = "http://localhost:9500"

    # API 端点
    API_CREATE_INSTANCE: str = "/api/v1/instances"
    API_GET_INSTANCE: str = "/api/v1/instances/{instance_id}"
    API_LIST_INSTANCES: str = "/api/v1/instances"
    API_DELETE_INSTANCE: str = "/api/v1/instances/{instance_id}"
    API_INSTANCE_HEALTH: str = "/api/v1/instances/{instance_id}/health"
    API_SERVICE_HEALTH: str = "/api/v1/health"

    # HTTP 超时
    HTTP_TIMEOUT: float = 30.0

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        use_browser_service: Optional[bool] = None,
    ):
        """
        Args:
            base_url: Browser-Service 地址, 默认从环境变量读取或使用 DEFAULT_BASE_URL
            use_browser_service: 强制使用/不使用 Browser-Service;
                None = 自动检测 (先尝试连接, 失败则回退)
        """
        self._base_url = (
            base_url
            or os.getenv("BROWSER_SERVICE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")

        self._use_browser_service = use_browser_service
        self._available: bool | None = None  # None = 尚未检测

        # 当前实例信息 (创建成功后填充)
        self._instance_id: Optional[str] = None
        self._cdp_port: Optional[int] = None
        self._ws_url: Optional[str] = None

        # 与 Playwright 的连接对象 (由 launch_and_connect 设置)
        self.browser: Optional[Any] = None  # playwright Browser 对象
        self.browser_context: Optional[Any] = None  # playwright BrowserContext 对象

        # Fallback: 本地 CDPBrowserManager (延迟导入)
        self._local_manager: Optional[Any] = None

        self._cleanup_registered = False

    # ------------------------------------------------------------------
    # 可用性检测
    # ------------------------------------------------------------------

    async def _check_availability(self) -> bool:
        """
        检测 Browser-Service 是否可达。

        Returns:
            True 如果服务可用, False 如果不可达
        """
        if self._available is not None:
            return self._available

        url = f"{self._base_url}{self.API_SERVICE_HEALTH}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    self._available = True
                    utils.logger.info(
                        f"[BrowserServiceClient] Browser-Service is available at {self._base_url}"
                    )
                    return True
        except httpx.ConnectError:
            utils.logger.warning(
                f"[BrowserServiceClient] Cannot connect to Browser-Service at {self._base_url}"
            )
        except httpx.TimeoutException:
            utils.logger.warning(
                f"[BrowserServiceClient] Connection to Browser-Service timed out: {self._base_url}"
            )
        except Exception as e:
            utils.logger.warning(
                f"[BrowserServiceClient] Unexpected error checking Browser-Service: {e}"
            )

        self._available = False
        return False

    async def _should_use_browser_service(self) -> bool:
        """判断是否应使用 Browser-Service (包括自动检测逻辑)"""
        if self._use_browser_service is not None:
            return self._use_browser_service
        return await self._check_availability()

    # ------------------------------------------------------------------
    # HTTP 客户端辅助
    # ------------------------------------------------------------------

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=self.HTTP_TIMEOUT)

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """
        向 Browser-Service 发送 HTTP 请求。

        Args:
            method: HTTP 方法 (GET/POST/PUT/DELETE)
            path: API 路径 (如 /api/v1/instances)
            **kwargs: 传给 httpx 的额外参数 (json, params 等)

        Returns:
            httpx.Response 对象

        Raises:
            httpx.HTTPStatusError: 如果响应状态码不是 2xx
            httpx.RequestError: 如果请求失败
        """
        url = f"{self._base_url}{path}"
        utils.logger.debug(
            f"[BrowserServiceClient] {method} {url}"
        )
        async with self._make_client() as client:
            resp = await client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp

    # ------------------------------------------------------------------
    # API 操作
    # ------------------------------------------------------------------

    async def create_instance(
        self,
        proxy: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
        headless: bool = True,
        platform: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        从 Browser-Service 池中创建一个浏览器实例。

        Args:
            proxy: 代理配置 (可选, CDP 模式下浏览器已启动, 代理可能不生效)
            user_agent: 自定义 User-Agent
            headless: 是否无头模式
            platform: 平台标识 (如 xhs/dy/ks), 用于日志区分
            extra_args: 额外的 Chrome 启动参数

        Returns:
            实例信息字典:
            {
                "instance_id": "uuid",
                "cdp_port": 9222,
                "cdp_url": "http://browser-service:9222",
                "status": "running",
                "platform": "xhs",
            }

        Raises:
            RuntimeError: 如果 Browser-Service 返回错误
        """
        payload: Dict[str, Any] = {
            "headless": headless,
        }
        if proxy:
            payload["proxy"] = proxy
        if user_agent:
            payload["user_agent"] = user_agent
        if platform:
            payload["platform"] = platform
        if extra_args:
            payload["extra_args"] = extra_args

        utils.logger.info(
            f"[BrowserServiceClient] Requesting browser instance from Browser-Service"
            f" (platform={platform}, headless={headless})"
        )

        try:
            resp = await self._request(
                "POST", self.API_CREATE_INSTANCE, json=payload
            )
        except httpx.RequestError as e:
            utils.logger.error(
                f"[BrowserServiceClient] Failed to create browser instance: {e}"
            )
            raise RuntimeError(
                f"Failed to create browser instance from Browser-Service: {e}"
            ) from e

        data = resp.json()
        if not data.get("success"):
            error_msg = data.get("error", "Unknown error")
            raise RuntimeError(
                f"Browser-Service rejected instance creation: {error_msg}"
            )

        instance = data.get("instance", {})
        utils.logger.info(
            f"[BrowserServiceClient] Browser instance created: "
            f"id={instance.get('instance_id')}, port={instance.get('cdp_port')}"
        )
        return instance

    async def delete_instance(self, instance_id: Optional[str] = None) -> bool:
        """
        销毁浏览器实例。

        Args:
            instance_id: 实例 ID, 默认使用当前实例

        Returns:
            True 如果删除成功
        """
        instance_id = instance_id or self._instance_id
        if not instance_id:
            utils.logger.warning(
                "[BrowserServiceClient] No instance_id to delete"
            )
            return False

        path = self.API_DELETE_INSTANCE.format(instance_id=instance_id)
        try:
            resp = await self._request("DELETE", path)
            data = resp.json()
            success = data.get("success", False)
            utils.logger.info(
                f"[BrowserServiceClient] Browser instance {instance_id} "
                f"{'deleted' if success else 'deletion failed'}"
            )
            return success
        except httpx.RequestError as e:
            utils.logger.warning(
                f"[BrowserServiceClient] Failed to delete instance {instance_id}: {e}"
            )
            return False

    async def get_instance_info(
        self, instance_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取浏览器实例详细信息。

        Args:
            instance_id: 实例 ID, 默认使用当前实例

        Returns:
            实例信息字典, 如果获取失败返回 None
        """
        instance_id = instance_id or self._instance_id
        if not instance_id:
            return None

        path = self.API_GET_INSTANCE.format(instance_id=instance_id)
        try:
            resp = await self._request("GET", path)
            data = resp.json()
            return data.get("instance")
        except httpx.RequestError as e:
            utils.logger.warning(
                f"[BrowserServiceClient] Failed to get instance info: {e}"
            )
            return None

    async def list_instances(self) -> List[Dict[str, Any]]:
        """
        列出 Browser-Service 中所有运行中的实例。

        Returns:
            实例信息列表
        """
        try:
            resp = await self._request("GET", self.API_LIST_INSTANCES)
            data = resp.json()
            return data.get("instances", [])
        except httpx.RequestError as e:
            utils.logger.warning(
                f"[BrowserServiceClient] Failed to list instances: {e}"
            )
            return []

    async def health_check(self) -> Dict[str, Any]:
        """
        检查 Browser-Service 服务健康状态。

        Returns:
            健康信息字典:
            {
                "status": "healthy",
                "pool_size": 5,
                "active_instances": 3,
                "available_slots": 2,
            }
        """
        try:
            resp = await self._request("GET", self.API_SERVICE_HEALTH)
            return resp.json()
        except httpx.RequestError as e:
            utils.logger.warning(
                f"[BrowserServiceClient] Health check failed: {e}"
            )
            return {"status": "unreachable", "error": str(e)}

    async def instance_health(
        self, instance_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检查指定浏览器实例的健康状态。

        Args:
            instance_id: 实例 ID, 默认使用当前实例

        Returns:
            健康信息字典: {"healthy": true, "uptime": 123, ...}
        """
        instance_id = instance_id or self._instance_id
        if not instance_id:
            return {"healthy": False, "error": "no instance_id"}

        path = self.API_INSTANCE_HEALTH.format(instance_id=instance_id)
        try:
            resp = await self._request("GET", path)
            return resp.json()
        except httpx.RequestError as e:
            return {"healthy": False, "error": str(e)}

    # ------------------------------------------------------------------
    # 核心方法: launch_and_connect (替代 CDPBrowserManager)
    # ------------------------------------------------------------------

    async def launch_and_connect(
        self,
        playwright: Any,
        playwright_proxy: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
        headless: bool = False,
        platform: Optional[str] = None,
    ) -> Any:
        """
        启动浏览器并连接 — 与 CDPBrowserManager.launch_and_connect 相同接口。

        工作流程:
          1. 检测 Browser-Service 是否可用
          2. 如果可用: POST /api/v1/instances → 获取 cdp_url
          3. playwright.chromium.connect_over_cdp(cdp_url) → 连接
          4. 如果不可用: 回退到本地 CDPBrowserManager

        Args:
            playwright: Playwright 实例 (来自 async_playwright().start())
            playwright_proxy: 代理配置 (CDP 模式下可能不生效)
            user_agent: 自定义 User-Agent
            headless: 是否无头模式
            platform: 平台标识 (用于日志和实例区分)

        Returns:
            BrowserContext 对象 (可直接用于页面操作)

        Raises:
            RuntimeError: 如果 Browser-Service 和本地启动都失败
        """
        should_use = await self._should_use_browser_service()

        if should_use:
            utils.logger.info(
                "[BrowserServiceClient] Using Browser-Service for browser management"
            )
            return await self._launch_via_service(
                playwright=playwright,
                proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
                platform=platform,
            )
        else:
            utils.logger.info(
                "[BrowserServiceClient] Browser-Service unavailable, "
                "falling back to local CDP browser management"
            )
            return await self._launch_via_local(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

    async def _launch_via_service(
        self,
        playwright: Any,
        proxy: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
        headless: bool = False,
        platform: Optional[str] = None,
    ) -> Any:
        """
        通过 Browser-Service 启动浏览器实例。
        """
        # 1. 从 Browser-Service 获取实例
        instance = await self.create_instance(
            proxy=proxy,
            user_agent=user_agent,
            headless=headless,
            platform=platform,
        )

        self._instance_id = instance["instance_id"]
        self._cdp_port = instance["cdp_port"]

        # 从 base_url 提取主机名, 用于构造 CDP URL
        # 在 Docker 网络中主机名如 "browser-service", 本地开发环境为 "localhost"
        default_cdp_host = urlparse(self._base_url).hostname or "localhost"
        cdp_url = instance.get("cdp_url", f"http://{default_cdp_host}:{self._cdp_port}")

        utils.logger.info(
            f"[BrowserServiceClient] Connecting to remote browser via CDP: {cdp_url}"
        )

        # 2. 通过 CDP 连接远程浏览器
        try:
            # connect_over_cdp 支持 http:// 和 ws:// 两种格式
            # http:// 格式会自动通过 /json/version 获取 WebSocket URL
            self.browser = await playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            utils.logger.error(
                f"[BrowserServiceClient] Failed to connect to remote browser "
                f"at {cdp_url}: {e}"
            )
            # 连接失败: 销毁远程实例
            await self.delete_instance()
            self._instance_id = None
            self._cdp_port = None
            raise RuntimeError(f"CDP connection failed: {e}") from e

        if not self.browser.is_connected():
            await self.delete_instance()
            self._instance_id = None
            self._cdp_port = None
            raise RuntimeError("CDP connection established but browser not connected")

        utils.logger.info(
            f"[BrowserServiceClient] Connected to remote browser "
            f"(contexts: {len(self.browser.contexts)})"
        )

        # 3. 创建或获取浏览器上下文
        contexts = self.browser.contexts
        if contexts:
            browser_context = contexts[0]
            utils.logger.info("[BrowserServiceClient] Using existing browser context")
        else:
            context_options: Dict[str, Any] = {
                "viewport": {"width": 1920, "height": 1080},
                "accept_downloads": True,
            }
            if user_agent:
                context_options["user_agent"] = user_agent

            if proxy:
                utils.logger.warning(
                    "[BrowserServiceClient] Proxy settings may not work in CDP mode; "
                    "consider configuring proxy at the Browser-Service level"
                )

            browser_context = await self.browser.new_context(**context_options)
            utils.logger.info("[BrowserServiceClient] Created new browser context")

        self.browser_context = browser_context
        return browser_context

    async def _launch_via_local(
        self,
        playwright: Any,
        playwright_proxy: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
        headless: bool = False,
    ) -> Any:
        """
        回退到本地 CDPBrowserManager 启动浏览器。

        延迟导入 CDPBrowserManager, 避免在没有本地 Chrome 时报错。
        """
        try:
            from tools.cdp_browser import CDPBrowserManager
        except ImportError as e:
            raise RuntimeError(
                "Cannot import CDPBrowserManager for fallback. "
                "Please ensure Crawler-Service is properly installed."
            ) from e

        self._local_manager = CDPBrowserManager()
        return await self._local_manager.launch_and_connect(
            playwright=playwright,
            playwright_proxy=playwright_proxy,
            user_agent=user_agent,
            headless=headless,
        )

    # ------------------------------------------------------------------
    # 反检测 & Cookie 辅助 (透传)
    # ------------------------------------------------------------------

    async def add_stealth_script(self, script_path: str = "libs/stealth.min.js"):
        """
        添加反检测脚本 (需有 browser_context)。

        注: 如果使用 Browser-Service 远程模式, stealth 脚本注入方式与本地相同。
        """
        if self.browser_context and os.path.exists(script_path):
            try:
                await self.browser_context.add_init_script(path=script_path)
                utils.logger.info(
                    f"[BrowserServiceClient] Added stealth script: {script_path}"
                )
            except Exception as e:
                utils.logger.warning(
                    f"[BrowserServiceClient] Failed to add stealth script: {e}"
                )

    async def add_cookies(self, cookies: List[Dict[str, Any]]):
        """添加 Cookies 到当前上下文"""
        if self.browser_context:
            try:
                await self.browser_context.add_cookies(cookies)
                utils.logger.info(
                    f"[BrowserServiceClient] Added {len(cookies)} cookies"
                )
            except Exception as e:
                utils.logger.warning(
                    f"[BrowserServiceClient] Failed to add cookies: {e}"
                )

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """获取当前上下文的 Cookies"""
        if self.browser_context:
            try:
                return await self.browser_context.cookies()
            except Exception as e:
                utils.logger.warning(
                    f"[BrowserServiceClient] Failed to get cookies: {e}"
                )
        return []

    # ------------------------------------------------------------------
    # 连接状态
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """
        检查浏览器是否仍然连接。

        优先检查远程 Browser 连接, 如果使用本地 CDPBrowserManager 则委派。
        """
        if self._local_manager is not None:
            return self._local_manager.is_connected()

        if self.browser is not None:
            try:
                return self.browser.is_connected()
            except Exception:
                pass
        return False

    async def get_browser_info(self) -> Dict[str, Any]:
        """
        获取浏览器信息 (兼容 CDPBrowserManager 接口)。

        Returns:
            浏览器信息字典
        """
        if self._local_manager is not None:
            return await self._local_manager.get_browser_info()

        info: Dict[str, Any] = {
            "instance_id": self._instance_id,
            "cdp_port": self._cdp_port,
            "is_connected": self.is_connected(),
        }

        if self.browser and self.browser.is_connected():
            try:
                info["version"] = self.browser.version
                info["contexts_count"] = len(self.browser.contexts)
            except Exception:
                pass

        return info

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    async def cleanup(self, force: bool = False):
        """
        清理浏览器资源。

        工作流程:
          1. 关闭 browser_context (page 关闭)
          2. 断开 browser 连接
          3. 如果是 Browser-Service 模式: 调用 DELETE /api/v1/instances/{id}
          4. 如果是本地模式: 委派给 CDPBrowserManager.cleanup()

        Args:
            force: 是否强制清理 (传递给本地 CDPBrowserManager)
        """
        # 1. 关闭浏览器上下文
        if self.browser_context:
            try:
                await self.browser_context.close()
                utils.logger.info("[BrowserServiceClient] Browser context closed")
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    utils.logger.warning(
                        f"[BrowserServiceClient] Error closing context: {e}"
                    )
            finally:
                self.browser_context = None

        # 2. 断开浏览器连接
        if self.browser:
            try:
                if self.browser.is_connected():
                    await self.browser.close()
                    utils.logger.info("[BrowserServiceClient] Browser connection closed")
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    utils.logger.warning(
                        f"[BrowserServiceClient] Error closing browser: {e}"
                    )
            finally:
                self.browser = None

        # 3. 如果是 Browser-Service 模式, 通知销毁实例
        if self._instance_id:
            await self.delete_instance()
            self._instance_id = None
            self._cdp_port = None

        # 4. 如果是本地 CDPBrowserManager 模式, 委派清理
        if self._local_manager:
            await self._local_manager.cleanup(force=force)

    # ------------------------------------------------------------------
    # 上下文管理器支持
    # ------------------------------------------------------------------

    async def __aenter__(self):
        """支持 async with 语句"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出时自动清理"""
        await self.cleanup()
        return False

    # ------------------------------------------------------------------
    # 静态方法: 快速检查 Browser-Service 可用性
    # ------------------------------------------------------------------

    @staticmethod
    async def quick_check(
        base_url: Optional[str] = None,
    ) -> bool:
        """
        快速检查 Browser-Service 是否可用 (不创建客户端实例)。

        Args:
            base_url: Browser-Service 地址, 默认从环境变量读取

        Returns:
            True 如果服务可用
        """
        base_url = (
            base_url
            or os.getenv("BROWSER_SERVICE_URL")
            or BrowserServiceClient.DEFAULT_BASE_URL
        ).rstrip("/")

        url = f"{base_url}{BrowserServiceClient.API_SERVICE_HEALTH}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False
