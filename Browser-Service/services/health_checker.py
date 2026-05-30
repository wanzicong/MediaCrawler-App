# -*- coding: utf-8 -*-
"""
Health Checker - 浏览器实例健康检查与自动恢复服务

功能:
- 心跳机制：每 15 秒对所有 ready 实例执行健康检查
- 自动恢复：连续 3 次失败 → 标记 unhealthy → 自动重启
- 僵尸清理：每 60 秒扫描，清理 stopped 超过 5 分钟的元数据
- 保活：对 CDP WebSocket 保持心跳 ping (通过 HTTP /json/version)
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

from services.browser_pool import BrowserPool

logger = logging.getLogger("health_checker")

# 配置常量
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "15"))        # 心跳间隔 (秒)
AUTO_RESTART_ENABLED = os.getenv("AUTO_RESTART_ENABLED", "true").lower() == "true"
MAX_HEALTH_FAIL_COUNT = int(os.getenv("MAX_HEALTH_FAIL_COUNT", "3"))   # 连续失败阈值
STALE_CLEANUP_INTERVAL = int(os.getenv("STALE_CLEANUP_INTERVAL", "60"))  # 僵尸清理间隔 (秒)
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "30"))             # WebSocket 保活间隔 (秒)


class HealthChecker:
    """
    健康检查器

    在后台 asyncio 任务中运行，周期性检查所有浏览器实例的健康状态
    """

    def __init__(self, pool: BrowserPool):
        self.pool = pool
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._ws_ping_task: Optional[asyncio.Task] = None
        self._start_time = time.time()

        logger.info(
            f"[HealthChecker] Initialized: heartbeat={HEARTBEAT_INTERVAL}s, "
            f"auto_restart={AUTO_RESTART_ENABLED}, fail_threshold={MAX_HEALTH_FAIL_COUNT}, "
            f"cleanup={STALE_CLEANUP_INTERVAL}s"
        )

    async def start(self):
        """启动后台健康检查任务"""
        if self._running:
            logger.warning("[HealthChecker] Already running")
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._ws_ping_task = asyncio.create_task(self._ws_ping_loop())

        logger.info("[HealthChecker] Started background tasks")

    async def stop(self):
        """停止后台健康检查任务"""
        self._running = False

        for task in [self._heartbeat_task, self._cleanup_task, self._ws_ping_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._heartbeat_task = None
        self._cleanup_task = None
        self._ws_ping_task = None

        logger.info("[HealthChecker] Stopped all background tasks")

    async def _heartbeat_loop(self):
        """
        心跳循环：周期性检查所有 ready 实例的健康状态
        """
        logger.info("[HealthChecker] Heartbeat loop started")

        while self._running:
            try:
                await self._check_all_instances()
            except Exception as e:
                logger.error(f"[HealthChecker] Error in heartbeat loop: {e}", exc_info=True)

            await asyncio.sleep(HEARTBEAT_INTERVAL)

        logger.info("[HealthChecker] Heartbeat loop stopped")

    async def _check_all_instances(self):
        """
        检查所有非 stopped 实例的健康状态
        """
        instances = await self.pool.list_instances()
        active_instances = [i for i in instances if i.status != "stopped"]

        if not active_instances:
            return

        for instance in active_instances:
            try:
                result = await self.pool.health_check_instance(instance.instance_id)

                if result["status"] == "unhealthy":
                    logger.warning(
                        f"[HealthChecker] Instance {instance.instance_id[:8]}... unhealthy "
                        f"(fail_count={instance.health_fail_count}/{MAX_HEALTH_FAIL_COUNT})"
                    )

                    # 达到连续失败阈值，自动重启
                    if AUTO_RESTART_ENABLED and instance.health_fail_count >= MAX_HEALTH_FAIL_COUNT:
                        logger.warning(
                            f"[HealthChecker] Auto-restarting instance {instance.instance_id[:8]}..."
                        )
                        try:
                            await self.pool.restart_instance(instance.instance_id)
                            logger.info(
                                f"[HealthChecker] Instance {instance.instance_id[:8]}... auto-restarted successfully"
                            )
                        except Exception as e:
                            logger.error(
                                f"[HealthChecker] Failed to auto-restart instance "
                                f"{instance.instance_id[:8]}...: {e}"
                            )
                elif result["status"] == "ok":
                    logger.debug(
                        f"[HealthChecker] Instance {instance.instance_id[:8]}... healthy "
                        f"(port={instance.debug_port})"
                    )

            except Exception as e:
                logger.error(
                    f"[HealthChecker] Error checking instance {instance.instance_id[:8]}...: {e}"
                )

    async def _cleanup_loop(self):
        """
        僵尸清理循环：周期性清理 stopped 超过 5 分钟的实例元数据
        """
        logger.info("[HealthChecker] Stale cleanup loop started")

        while self._running:
            try:
                await self.pool.cleanup_stale_instances(max_age_seconds=300)
            except Exception as e:
                logger.error(f"[HealthChecker] Error in cleanup loop: {e}", exc_info=True)

            await asyncio.sleep(STALE_CLEANUP_INTERVAL)

        logger.info("[HealthChecker] Stale cleanup loop stopped")

    async def _ws_ping_loop(self):
        """
        CDP WebSocket 保活循环

        通过 HTTP GET /json/version 保持 CDP 连接活跃，
        防止长时间无活动导致浏览器自动关闭调试端口。
        """
        logger.info("[HealthChecker] WebSocket ping loop started")

        while self._running:
            try:
                instances = await self.pool.list_instances()
                ready_instances = [i for i in instances if i.status == "ready"]

                async with httpx.AsyncClient() as client:
                    for instance in ready_instances:
                        try:
                            resp = await client.get(
                                f"http://localhost:{instance.debug_port}/json/version",
                                timeout=5,
                            )
                            if resp.status_code == 200:
                                logger.debug(
                                    f"[HealthChecker] WS ping OK: port={instance.debug_port}"
                                )
                            else:
                                logger.warning(
                                    f"[HealthChecker] WS ping failed: port={instance.debug_port}, "
                                    f"status={resp.status_code}"
                                )
                        except Exception as e:
                            logger.debug(
                                f"[HealthChecker] WS ping error: port={instance.debug_port}: {e}"
                            )

            except Exception as e:
                logger.error(f"[HealthChecker] Error in WS ping loop: {e}")

            await asyncio.sleep(WS_PING_INTERVAL)

        logger.info("[HealthChecker] WebSocket ping loop stopped")

    async def check_single(self, instance_id: str) -> dict:
        """
        手动触发单实例健康检查

        Returns:
            dict: 健康检查结果
        """
        return await self.pool.health_check_instance(instance_id)

    @property
    def uptime(self) -> float:
        """健康检查器运行时长"""
        return time.time() - self._start_time
