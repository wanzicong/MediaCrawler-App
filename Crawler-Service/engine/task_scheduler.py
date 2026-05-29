# -*- coding: utf-8 -*-
"""
多任务并行调度器

支持按平台分组、并发槽位控制、优先级排队。
替代原有的单例 CrawlerManager 单任务串行模式。
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .task_executor import TaskExecutor

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPING = "stopping"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: int
    platform: str
    crawler_type: str
    config: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __lt__(self, other: "ScheduledTask") -> bool:
        """优先级队列排序"""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


class TaskScheduler:
    """
    多任务并行调度器

    特性:
    - 可配置的最大并发数 (max_concurrent)
    - 同一平台的任务自动排队 (per_platform_queue=True)
    - 优先级调度
    - 任务状态追踪
    - 优雅关闭
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        per_platform_queue: bool = False,
    ):
        self.max_concurrent = max_concurrent
        self.per_platform_queue = per_platform_queue

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running: Dict[int, asyncio.Task] = {}
        self._waiting: List[ScheduledTask] = []
        self._platform_running_count: Dict[str, int] = {}
        self._all_tasks: Dict[int, ScheduledTask] = {}
        self._lock = asyncio.Lock()
        self._shutdown = False
        self._log_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    def get_log_queue(self) -> asyncio.Queue:
        return self._log_queue

    async def push_log(self, message: str, level: str = "info") -> None:
        try:
            self._log_queue.put_nowait({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message,
            })
        except asyncio.QueueFull:
            pass

    async def submit(
        self,
        config: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> int:
        """提交任务到调度器，返回 task_id"""
        async with self._lock:
            if self._shutdown:
                raise RuntimeError("Scheduler is shutting down")

            task = await self._create_task_via_api(config)
            task_id = task["task_id"]

            scheduled = ScheduledTask(
                task_id=task_id,
                platform=config.get("platform", "xhs"),
                crawler_type=config.get("crawler_type", "search"),
                config=config,
                priority=priority,
            )
            self._all_tasks[task_id] = scheduled

            if self._can_start_now(scheduled.platform):
                await self._start_task(scheduled)
            else:
                scheduled.status = TaskStatus.QUEUED
                self._waiting.append(scheduled)
                self._waiting.sort()
                pos = self._waiting.index(scheduled) + 1
                await self.push_log(
                    f"Task #{task_id} ({scheduled.platform}) queued (position {pos})"
                )

            return task_id

    async def stop_task(self, task_id: int) -> bool:
        async with self._lock:
            if task_id in self._running:
                task = self._all_tasks.get(task_id)
                if task:
                    task.status = TaskStatus.STOPPING
                self._running[task_id].cancel()
                return True

            for i, t in enumerate(self._waiting):
                if t.task_id == task_id:
                    self._waiting.pop(i)
                    return True
            return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "max_concurrent": self.max_concurrent,
            "running_count": len(self._running),
            "waiting_count": len(self._waiting),
            "platform_running": dict(self._platform_running_count),
            "running": [
                {"task_id": tid, "platform": self._all_tasks[tid].platform}
                for tid in self._running if tid in self._all_tasks
            ],
            "waiting": [
                {"task_id": t.task_id, "platform": t.platform, "priority": t.priority}
                for t in self._waiting
            ],
        }

    async def shutdown(self, timeout: float = 30.0) -> None:
        async with self._lock:
            self._shutdown = True

        await self.push_log("Scheduler shutting down...", "warning")

        for task_id in list(self._running.keys()):
            await self.stop_task(task_id)

        if self._running:
            running_tasks = list(self._running.values())
            try:
                await asyncio.wait_for(
                    asyncio.gather(*running_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                await self.push_log("Some tasks timed out during shutdown", "error")

        await self.push_log("Scheduler shut down", "info")

    def _can_start_now(self, platform: str) -> bool:
        total = len(self._running)
        if total >= self.max_concurrent:
            return False
        if self.per_platform_queue:
            platform_count = self._platform_running_count.get(platform, 0)
            if platform_count >= max(1, self.max_concurrent // 2):
                return False
        return True

    async def _start_task(self, scheduled: ScheduledTask) -> None:
        scheduled.status = TaskStatus.RUNNING
        scheduled.started_at = datetime.now()

        self._platform_running_count[scheduled.platform] = \
            self._platform_running_count.get(scheduled.platform, 0) + 1

        await self.push_log(
            f"Task #{scheduled.task_id} ({scheduled.platform}/{scheduled.crawler_type}) started"
        )

        async def _runner():
            await self._semaphore.acquire()
            try:
                executor = TaskExecutor(scheduled.task_id, scheduled.config)
                result = await executor.run()

                async with self._lock:
                    scheduled.completed_at = datetime.now()
                    if result.get("status") == "completed":
                        scheduled.status = TaskStatus.COMPLETED
                        await self.push_log(
                            f"Task #{scheduled.task_id} done ({result.get('notes_crawled', 0)} items)",
                            "success"
                        )
                    else:
                        scheduled.status = TaskStatus.FAILED
                        await self.push_log(
                            f"Task #{scheduled.task_id} failed: {result.get('error', '')}",
                            "error"
                        )
            except asyncio.CancelledError:
                scheduled.status = TaskStatus.FAILED
                await self.push_log(f"Task #{scheduled.task_id} cancelled", "warning")
            except Exception as e:
                scheduled.status = TaskStatus.FAILED
                await self.push_log(f"Task #{scheduled.task_id} error: {e}", "error")
            finally:
                self._semaphore.release()
                async with self._lock:
                    self._running.pop(scheduled.task_id, None)
                    count = self._platform_running_count.get(scheduled.platform, 0)
                    if count > 0:
                        self._platform_running_count[scheduled.platform] = count - 1
                    await self._dequeue_next()

        self._running[scheduled.task_id] = asyncio.create_task(_runner())

    async def _dequeue_next(self) -> None:
        if not self._waiting or self._shutdown:
            return

        for i, task in enumerate(self._waiting):
            if self._can_start_now(task.platform):
                self._waiting.pop(i)
                await self._start_task(task)
                return

    async def _create_task_via_api(self, config: Dict[str, Any]) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{DATA_API_URL}/api/internal/tasks",
                    json={"payload": config, "profile_id": config.get("profile_id")},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            fake_id = len(self._all_tasks) + 1
            return {"task_id": fake_id}


# 全局单例
scheduler = TaskScheduler(max_concurrent=3)

