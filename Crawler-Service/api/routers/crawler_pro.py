# -*- coding: utf-8 -*-
"""
MediaCrawler Pro API 路由

多任务并行、断点续爬、多账号管理
"""

import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..schemas import CrawlerStartRequest
from engine.task_scheduler import scheduler, TaskPriority as TP
from engine.checkpoint import CheckpointManager, CHECKPOINT_DIR
from engine.account_manager import AccountManager

router = APIRouter(prefix="/crawler-pro", tags=["crawler-pro"])
DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


# ==================== 多任务并行 ====================

@router.post("/start")
async def start_crawler_pro(
    request: CrawlerStartRequest,
    priority: str = Query("normal"),
    resume: bool = Query(True),
):
    config = request.model_dump(mode="json", exclude_none=True)
    config["resume"] = resume
    prio_map = {"low": TP.LOW, "normal": TP.NORMAL, "high": TP.HIGH, "urgent": TP.URGENT}
    prio = prio_map.get(priority, TP.NORMAL)
    try:
        task_id = await scheduler.submit(config, priority=prio)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"status": "ok", "task_id": task_id, "priority": priority, "resume": resume}


@router.post("/stop/{task_id}")
async def stop_crawler_pro(task_id: int):
    ok = await scheduler.stop_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"status": "ok", "message": f"Task {task_id} stopped"}


@router.get("/status")
async def get_scheduler_status():
    return scheduler.get_status()


@router.post("/shutdown")
async def shutdown_scheduler():
    await scheduler.shutdown(timeout=30.0)
    return {"status": "ok"}


# ==================== 断点续爬 ====================

@router.get("/checkpoint/{task_id}")
async def get_checkpoint(task_id: int):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}/checkpoint")
            if resp.status_code == 200:
                return {"status": "ok", "task_id": task_id, "checkpoint": resp.json()}
    except Exception:
        pass
    return {"status": "ok", "task_id": task_id, "checkpoint": None}


@router.delete("/checkpoint/{task_id}")
async def delete_checkpoint(task_id: int):
    cp_file = CHECKPOINT_DIR / f"checkpoint_{task_id}.json"
    if cp_file.exists():
        cp_file.unlink()
        return {"status": "ok", "message": f"Checkpoint deleted"}
    return {"status": "ok", "message": "No checkpoint found"}


# ==================== 多账号管理 ====================

@router.get("/accounts/{platform}")
async def list_accounts(platform: str):
    manager = AccountManager(platform, enable_ip_proxy=False)
    await manager.load_accounts()
    return manager.get_status()


@router.post("/accounts/{platform}/refresh")
async def refresh_accounts(platform: str):
    manager = AccountManager(platform, enable_ip_proxy=False)
    count = await manager.load_accounts()
    return {"status": "ok", "platform": platform, "accounts_loaded": count}


# ==================== 配置 ====================

@router.get("/config")
async def get_pro_config():
    return {
        "max_concurrent": scheduler.max_concurrent,
        "per_platform_queue": scheduler.per_platform_queue,
        "features": {
            "multi_task": True, "checkpoint_resume": True,
            "multi_account": True, "ip_proxy_pool": True,
            "signer_service": True, "homefeed": True, "trending": True,
        },
    }


@router.post("/config/max-concurrent")
async def set_max_concurrent(count: int = Query(3, ge=1, le=10)):
    scheduler.max_concurrent = count
    return {"status": "ok", "max_concurrent": count}
