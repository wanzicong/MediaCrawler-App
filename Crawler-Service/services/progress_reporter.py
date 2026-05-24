# -*- coding: utf-8 -*-
"""爬取进度上报 — 子进程定时通过 HTTP 将进度写入 Data API Service"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class ProgressReporter:
    """轻量进度上报器，子进程通过 task_id 定时 PUT 进度到 Data API"""

    def __init__(self, task_id: int, flush_interval: float = 5.0):
        self._task_id = task_id
        self._flush_interval = flush_interval
        self._current: dict = {}
        self._dirty = False
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()

    async def report(self, **kwargs):
        async with self._lock:
            self._current.update(kwargs)
            self._dirty = True

    async def _periodic_flush(self):
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush()

    async def _flush(self):
        async with self._lock:
            if not self._dirty:
                return
            data = dict(self._current)
            self._dirty = False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(
                    f"{DATA_API_URL}/api/internal/tasks/{self._task_id}/progress",
                    json={"progress": data.get("progress", 0), "message": data.get("message", "")},
                )
        except Exception:
            pass  # 进度上报失败不应中断爬虫


_progress_reporter: Optional[ProgressReporter] = None


def init_progress_reporter(task_id: int) -> ProgressReporter:
    global _progress_reporter
    _progress_reporter = ProgressReporter(task_id)
    return _progress_reporter


def get_progress_reporter() -> Optional[ProgressReporter]:
    return _progress_reporter
