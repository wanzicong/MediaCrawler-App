# -*- coding: utf-8 -*-
"""
单任务执行器

整合所有 Pro 版本功能：
- 断点续爬 (CheckpointManager)
- 多账号 + IP代理池 (AccountManager)
- 浏览器抽象 (Browser 接口)
- 签名服务调用
- 进度上报
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Type

import httpx

from .checkpoint import CheckpointManager
from .account_manager import AccountManager, ScheduleStrategy

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class TaskExecutor:
    """
    单任务执行器

    每个 TaskExecutor 拥有独立的:
    - CheckpointManager (断点续爬)
    - AccountManager (账号+代理)
    - BrowserContext (浏览器上下文)
    - 签名服务客户端

    生命周期: init() -> prepare() -> run() -> cleanup()
    """

    def __init__(self, task_id: int, task_config: Dict[str, Any]):
        self.task_id = task_id
        self.config = task_config
        self.platform = task_config.get("platform", "xhs")
        self.crawler_type = task_config.get("crawler_type", "search")
        self.keywords = task_config.get("keywords", "")

        # 核心组件
        self.checkpoint: Optional[CheckpointManager] = None
        self.account_manager: Optional[AccountManager] = None

        # 浏览器相关
        self.browser_context: Any = None
        self._playwright: Any = None

        # 状态
        self.status = "pending"
        self.error_message: str = ""

        # 进度上报
        self._reporter: Any = None

    # ---------- 生命周期 ----------

    async def prepare(self) -> bool:
        """准备阶段：初始化断点续爬、账号管理、加载配置"""
        try:
            # 1. 断点续爬管理器
            self.checkpoint = CheckpointManager(
                task_id=self.task_id,
                platform=self.platform,
                crawler_type=self.crawler_type,
            )
            cp = await self.checkpoint.init(keywords=self.keywords)

            if cp.total_crawled > 0:
                print(f"[TaskExecutor #{self.task_id}] 恢复进度: "
                      f"已爬={cp.total_crawled} 页={cp.current_page}")

            # 2. 多账号管理器
            enable_proxy = self.config.get("enable_ip_proxy", False)
            proxy_count = self.config.get("ip_proxy_pool_count", 2)
            self.account_manager = AccountManager(
                platform=self.platform,
                strategy=ScheduleStrategy.LEAST_USED,
                enable_ip_proxy=enable_proxy,
                ip_proxy_pool_count=proxy_count,
            )
            await self.account_manager.load_accounts()

            # 3. 应用配置到全局 config 模块 (兼容现有爬虫代码)
            self._apply_config()

            # 4. 启动进度上报
            await self._start_progress_reporter()

            return True
        except Exception as e:
            print(f"[TaskExecutor #{self.task_id}] 准备失败: {e}")
            self.status = "error"
            self.error_message = str(e)
            await self._mark_task_finished(False, str(e))
            return False

    async def run(self) -> Dict[str, Any]:
        """执行爬取"""
        if not await self.prepare():
            return {"task_id": self.task_id, "status": "error", "error": self.error_message}

        self.status = "running"
        success = True
        result: Dict[str, Any] = {"task_id": self.task_id, "notes_crawled": 0}

        try:
            # 获取账号和代理
            account, proxy = await self.account_manager.acquire()

            # 启动浏览器
            browser_ctx = await self._launch_browser(account, proxy)

            # 创建并执行爬虫
            crawler = self._create_crawler()
            crawler.browser_context = browser_ctx

            if hasattr(crawler, 'account_manager'):
                crawler.account_manager = self.account_manager
            if hasattr(crawler, 'checkpoint'):
                crawler.checkpoint = self.checkpoint

            await crawler.start()

            # 标记完成
            self.checkpoint.mark_completed()
            await self.checkpoint.save()

            result["notes_crawled"] = self.checkpoint.cp.total_crawled
            result["status"] = "completed"

        except Exception as e:
            success = False
            self.error_message = str(e)
            traceback.print_exc()
            result["status"] = "failed"
            result["error"] = str(e)

            # 限流/风控判断
            error_lower = str(e).lower()
            if any(kw in error_lower for kw in ["rate limit", "too many", "429", "频繁"]):
                self.account_manager.mark_rate_limited()
            elif any(kw in error_lower for kw in ["banned", "封禁", "冻结"]):
                self.account_manager.mark_banned()

            # 保存断点
            if self.checkpoint:
                await self.checkpoint.save()

        finally:
            # 清理
            await self._cleanup_browser()
            if self.account_manager:
                await self.account_manager.release()
            await self._stop_progress_reporter()
            await self._mark_task_finished(success, self.error_message)

        return result

    async def stop(self) -> None:
        """停止任务 (优雅关闭)"""
        self.status = "stopping"
        if self.checkpoint:
            await self.checkpoint.save()

    # ---------- 内部实现 ----------

    def _create_crawler(self):
        """创建平台爬虫实例"""
        from main import CrawlerFactory
        return CrawlerFactory.create_crawler(platform=self.platform)

    async def _launch_browser(self, account, proxy) -> Any:
        """启动浏览器并创建上下文"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        launch_options: Dict[str, Any] = {
            "headless": self.config.get("headless", False),
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }

        # 代理配置
        if proxy:
            launch_options["proxy"] = {
                "server": f"http://{proxy['ip']}:{proxy['port']}",
            }
            if proxy.get("user") and proxy.get("password"):
                launch_options["proxy"]["username"] = proxy["user"]
                launch_options["proxy"]["password"] = proxy["password"]

        browser = await self._playwright.chromium.launch(**launch_options)

        context_options: Dict[str, Any] = {
            "viewport": {"width": 1920, "height": 1080},
        }

        # 注入账号 Cookie
        if account and account.cookies:
            if browser.contexts:
                await browser.contexts[0].add_cookies([
                    {"name": k, "value": v, "domain": self._get_domain(), "path": "/"}
                    for k, v in account.cookies.items()
                ])

        # User Agent
        if account and account.user_agent:
            context_options["user_agent"] = account.user_agent

        context = await browser.new_context(**context_options)
        print(f"[TaskExecutor #{self.task_id}] 浏览器已启动")
        return context

    def _get_domain(self) -> str:
        domains = {
            "xhs": ".xiaohongshu.com", "bili": ".bilibili.com",
            "dy": ".douyin.com", "ks": ".kuaishou.com",
            "wb": ".weibo.com", "tieba": ".baidu.com",
            "zhihu": ".zhihu.com",
        }
        return domains.get(self.platform, ".com")

    async def _cleanup_browser(self) -> None:
        if self.browser_context:
            try:
                await self.browser_context.close()
            except Exception:
                pass
            self.browser_context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def _apply_config(self) -> None:
        """将任务配置应用到全局 config 模块"""
        from config.applier import apply_crawler_payload
        apply_crawler_payload(self.config)

        import config as _cfg
        _cfg.TASK_ID = self.task_id

    async def _start_progress_reporter(self) -> None:
        try:
            from services.progress_reporter import ProgressReporter
            self._reporter = ProgressReporter(self.task_id, flush_interval=5.0)
            await self._reporter.start()
        except Exception:
            self._reporter = None

    async def _stop_progress_reporter(self) -> None:
        if self._reporter:
            try:
                await self._reporter.stop()
            except Exception:
                pass
            self._reporter = None

    async def _mark_task_finished(self, success: bool, error: str = "") -> None:
        status = "completed" if success else "failed"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(
                    f"{DATA_API_URL}/api/internal/tasks/{self.task_id}/finish",
                    json={"status": status, "error": error},
                )
        except Exception:
            pass

