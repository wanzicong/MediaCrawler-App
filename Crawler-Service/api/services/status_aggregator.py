# -*- coding: utf-8 -*-
"""聚合经典子进程调度与 Pro 进程内调度的运行状态"""

from __future__ import annotations

from typing import Any

from . import crawler_manager


def _get_pro_status() -> dict[str, Any] | None:
    try:
        from engine.task_scheduler import scheduler

        return scheduler.get_status()
    except Exception:
        return None


def get_combined_status() -> dict[str, Any]:
    """合并 CrawlerManager + TaskScheduler 状态，兼容原有 /api/crawler/status 字段"""
    classic = crawler_manager.get_status()
    pro = _get_pro_status()

    classic_tasks = [
        {**task, "source": "classic"}
        for task in classic.get("running_tasks", [])
    ]
    pro_tasks = []
    pro_queue = 0
    pro_running = 0

    if pro:
        pro_running = pro.get("running_count", 0)
        pro_queue = pro.get("waiting_count", 0)
        for task in pro.get("running", []):
            pro_tasks.append(
                {
                    "task_id": task.get("task_id"),
                    "platform": task.get("platform"),
                    "crawler_type": None,
                    "started_at": None,
                    "status": "running",
                    "source": "pro",
                }
            )

    running_tasks = classic_tasks + pro_tasks
    total_running = classic.get("running_count", 0) + pro_running
    total_queue = classic.get("queue_length", 0) + pro_queue
    first_task = running_tasks[0] if running_tasks else None

    return {
        "status": "running" if total_running > 0 else classic.get("status", "idle"),
        "platform": first_task.get("platform") if first_task else classic.get("platform"),
        "crawler_type": first_task.get("crawler_type") if first_task else classic.get("crawler_type"),
        "started_at": first_task.get("started_at") if first_task else classic.get("started_at"),
        "error_message": classic.get("error_message"),
        "task_id": first_task.get("task_id") if first_task else classic.get("task_id"),
        "queue_length": total_queue,
        "running_count": total_running,
        "max_concurrent": classic.get("max_concurrent", 3),
        "running_tasks": running_tasks,
        "schedulers": {
            "classic": classic,
            "pro": pro,
        },
    }
