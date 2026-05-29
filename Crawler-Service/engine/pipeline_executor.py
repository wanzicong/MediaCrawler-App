# -*- coding: utf-8 -*-
"""
任务管道执行器

支持三种执行模式：
- BATCH (批量并行) — 全部关键词同时提交到调度器
- QUEUE (排队串行) — 一个任务完成后再启动下一个
- CRON (定时) — 按 cron 表达式周期执行
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class PipelineMode(str, Enum):
    BATCH = "batch"
    QUEUE = "queue"
    CRON = "cron"


@dataclass
class PipelineTask:
    task_ref: str        # 任务引用 ID
    keyword: str
    platform: str
    crawler_type: str
    status: str = "pending"   # pending/running/completed/failed
    task_id: Optional[int] = None
    error: str = ""


@dataclass
class Pipeline:
    pipeline_id: str
    name: str
    platform: str
    keywords: List[str]
    mode: PipelineMode
    config: Dict[str, Any] = field(default_factory=dict)
    tasks: List[PipelineTask] = field(default_factory=list)
    status: str = "idle"
    progress: int = 0
    total: int = 0
    created_at: str = ""


class PipelineExecutor:
    """任务管道执行器"""

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._lock = asyncio.Lock()
        self._running: Dict[str, asyncio.Task] = {}

    async def create(
        self, name: str, platform: str,
        keywords: List[str], mode: PipelineMode = PipelineMode.BATCH,
        config: Optional[Dict[str, Any]] = None,
    ) -> Pipeline:
        """创建管道"""
        pipeline_id = str(uuid.uuid4())[:8]
        pipeline = Pipeline(
            pipeline_id=pipeline_id, name=name, platform=platform,
            keywords=keywords, mode=mode, config=config or {},
            tasks=[PipelineTask(
                task_ref=f"{pipeline_id}_{i}",
                keyword=kw, platform=platform,
                crawler_type=config.get("crawler_type", "search") if config else "search",
            ) for i, kw in enumerate(keywords)],
            total=len(keywords),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        async with self._lock:
            self._pipelines[pipeline_id] = pipeline
        return pipeline

    async def run(self, pipeline_id: str) -> Dict[str, Any]:
        """执行管道"""
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return {"error": f"管道 {pipeline_id} 不存在"}
            if pipeline.status == "running":
                return {"error": "管道正在运行中"}
            pipeline.status = "running"

        if pipeline.mode == PipelineMode.BATCH:
            asyncio.create_task(self._run_batch(pipeline))
        elif pipeline.mode == PipelineMode.QUEUE:
            asyncio.create_task(self._run_queue(pipeline))
        elif pipeline.mode == PipelineMode.CRON:
            self._run_cron(pipeline)

        return {"status": "ok", "pipeline_id": pipeline_id, "mode": pipeline.mode.value}

    async def stop(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return False
            pipeline.status = "stopped"

            if pipeline_id in self._running:
                self._running[pipeline_id].cancel()
                del self._running[pipeline_id]
            return True

    def get(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)

    def list_all(self) -> List[Pipeline]:
        return sorted(self._pipelines.values(), key=lambda p: p.created_at, reverse=True)

    def delete(self, pipeline_id: str) -> bool:
        if pipeline_id in self._pipelines:
            if self._pipelines[pipeline_id].status == "running":
                return False
            del self._pipelines[pipeline_id]
            return True
        return False

    # ---- 执行模式 ----

    async def _run_batch(self, pipeline: Pipeline) -> None:
        """批量并行：所有任务同时提交到 Scheduler"""
        try:
            from .task_scheduler import scheduler, TaskPriority

            for i, task in enumerate(pipeline.tasks):
                if pipeline.status == "stopped":
                    break
                task.status = "running"
                pipeline.progress = i + 1

                config = {
                    "platform": task.platform,
                    "crawler_type": task.crawler_type,
                    "keywords": task.keyword,
                    "save_option": "db",
                    **pipeline.config,
                }
                try:
                    tid = await scheduler.submit(config, priority=TaskPriority.NORMAL)
                    task.task_id = tid
                    task.status = "completed"
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)

                await asyncio.sleep(0.5)  # 提交间隔

            pipeline.status = "completed" if pipeline.status != "stopped" else "stopped"
            await self._sync_keyword_status(pipeline)
        except asyncio.CancelledError:
            pipeline.status = "stopped"

    async def _run_queue(self, pipeline: Pipeline) -> None:
        """排队串行：上一个完成再启动下一个"""
        try:
            from .task_scheduler import scheduler, TaskPriority

            for i, task in enumerate(pipeline.tasks):
                if pipeline.status == "stopped":
                    break
                task.status = "running"
                pipeline.progress = i + 1

                config = {
                    "platform": task.platform,
                    "crawler_type": task.crawler_type,
                    "keywords": task.keyword,
                    "save_option": "db",
                    **pipeline.config,
                }
                try:
                    tid = await scheduler.submit(config, priority=TaskPriority.NORMAL)
                    task.task_id = tid
                    # 等待任务完成
                    await self._wait_for_task(tid)
                    task.status = "completed"
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)

            pipeline.status = "completed" if pipeline.status != "stopped" else "stopped"
            await self._sync_keyword_status(pipeline)
        except asyncio.CancelledError:
            pipeline.status = "stopped"

    def _run_cron(self, pipeline: Pipeline) -> None:
        """定时执行：按间隔周期执行"""
        interval = pipeline.config.get("cron_interval", 3600)  # 默认1小时

        async def _cron_loop():
            while True:
                if pipeline.status == "stopped":
                    break
                await self._run_batch(pipeline)
                await asyncio.sleep(interval)

        self._running[pipeline.pipeline_id] = asyncio.create_task(_cron_loop())

    async def _wait_for_task(self, task_id: int, timeout: float = 600.0) -> bool:
        """等待单个调度器任务完成"""
        deadline = asyncio.get_event_loop().time() + timeout
        from .task_scheduler import scheduler

        while asyncio.get_event_loop().time() < deadline:
            status = scheduler.get_status()
            running_ids = [t["task_id"] for t in status.get("running", [])]
            if task_id not in running_ids:
                # 检查是否在 waiting 中
                waiting_ids = [t["task_id"] for t in status.get("waiting", [])]
                if task_id not in waiting_ids:
                    return True
            await asyncio.sleep(2.0)
        return False

    async def _sync_keyword_status(self, pipeline: Pipeline) -> None:
        """回写关键词状态到 Data-API"""
        for task in pipeline.tasks:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{DATA_API_URL}/api/keywords/status-sync",
                        json={
                            "keyword": task.keyword,
                            "platform": task.platform,
                            "task_id": task.task_id,
                            "status": task.status,
                        },
                    )
            except Exception:
                pass


# 全局实例
pipeline_executor = PipelineExecutor()
