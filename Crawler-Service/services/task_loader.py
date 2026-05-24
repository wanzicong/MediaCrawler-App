# -*- coding: utf-8 -*-
"""子进程按 task_id 从 Data API Service 加载配置（HTTP 通信）"""

from __future__ import annotations

import os

import httpx

from config.applier import apply_crawler_payload

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


async def apply_task_config(task_id: int) -> None:
    """从 Data API Service 获取任务配置并应用"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
        resp.raise_for_status()
        task_data = resp.json()

    payload = task_data.get("payload", {})
    apply_crawler_payload(payload)

    # 标记任务开始执行（progress 端点首次调用会自动 pending→running）
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.put(
            f"{DATA_API_URL}/api/internal/tasks/{task_id}/progress",
            json={"progress": 0, "message": "任务开始执行"},
        )

    # 初始化进度上报器
    from services.progress_reporter import init_progress_reporter, get_progress_reporter

    init_progress_reporter(task_id)
    reporter = get_progress_reporter()
    await reporter.start()
