# -*- coding: utf-8 -*-
"""内部 API — 供 Crawler Service 调用，零代码共享，纯 HTTP 通信"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from database.db_session import get_mysql_session
from database.system_models import CrawlerAccount, CrawlerTaskLog
from database.models import (
    BilibiliContactInfo,
    BilibiliUpDynamic,
    BilibiliUpInfo,
    BilibiliVideo,
    BilibiliVideoComment,
    DouyinAweme,
    DouyinAwemeComment,
    DyCreator,
    KuaishouVideo,
    KuaishouVideoComment,
    TiebaComment,
    TiebaCreator,
    TiebaNote,
    WeiboCreator,
    WeiboNote,
    WeiboNoteComment,
    XhsCreator,
    XhsNote,
    XhsNoteComment,
    ZhihuContent,
    ZhihuComment,
    ZhihuCreator,
)
from services.config_service import ConfigService

router = APIRouter(prefix="/api/internal", tags=["internal"])

# ── platform + kind → ORM model 映射 ──────────────────────────────
_MODEL_MAP: dict[tuple[str, str], Any] = {
    ("xhs", "content"): XhsNote,
    ("xhs", "comment"): XhsNoteComment,
    ("xhs", "creator"): XhsCreator,
    ("dy", "content"): DouyinAweme,
    ("dy", "comment"): DouyinAwemeComment,
    ("dy", "creator"): DyCreator,
    ("ks", "content"): KuaishouVideo,
    ("ks", "comment"): KuaishouVideoComment,
    ("bili", "content"): BilibiliVideo,
    ("bili", "comment"): BilibiliVideoComment,
    ("bili", "creator"): BilibiliUpInfo,
    ("bili", "contact"): BilibiliContactInfo,
    ("bili", "dynamic"): BilibiliUpDynamic,
    ("wb", "content"): WeiboNote,
    ("wb", "comment"): WeiboNoteComment,
    ("wb", "creator"): WeiboCreator,
    ("tieba", "content"): TiebaNote,
    ("tieba", "comment"): TiebaComment,
    ("tieba", "creator"): TiebaCreator,
    ("zhihu", "content"): ZhihuContent,
    ("zhihu", "comment"): ZhihuComment,
    ("zhihu", "creator"): ZhihuCreator,
}


# ── 请求/响应模型 ──────────────────────────────────────────────

class BatchDataRequest(BaseModel):
    platform: str
    kind: str  # content | comment | creator
    task_id: int
    records: list[dict[str, Any]]


class TaskProgressRequest(BaseModel):
    progress: int
    message: str = ""


class TaskFinishRequest(BaseModel):
    status: str  # completed | failed
    total_count: int = 0
    success_count: int = 0
    error: str = ""


class CreateTaskRequest(BaseModel):
    payload: dict[str, Any]
    profile_id: Optional[int] = None


# ── 内部 API 端点 ──────────────────────────────────────────────


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: int):
    """获取指定配置方案"""
    profile = await ConfigService.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    return profile


@router.post("/tasks")
async def create_task(body: CreateTaskRequest):
    """创建爬虫任务记录"""
    payload = dict(body.payload)
    payload["save_option"] = "db"
    task = await ConfigService.create_task(payload, body.profile_id)
    return {"task_id": task["id"]}


@router.get("/tasks")
async def list_tasks(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    platform: Optional[str] = None,
):
    """分页查询任务列表"""
    return await ConfigService.list_tasks_paginated(page=page, page_size=page_size, status=status, platform=platform)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除任务记录"""
    task = await ConfigService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    await ConfigService.delete_task(task_id)
    return {"status": "ok", "message": "任务已删除"}


@router.post("/data/batch")
async def batch_write_data(body: BatchDataRequest):
    """批量写入爬取数据到 MySQL"""
    model = _MODEL_MAP.get((body.platform, body.kind))
    if model is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform/kind: {body.platform}/{body.kind}",
        )

    if not body.records:
        return {"written": 0, "message": "no records to write"}

    now_ts = int(time.time() * 1000)
    written = 0

    try:
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        async with get_mysql_session() as session:
            for rec in body.records:
                rec.setdefault("task_id", body.task_id)
                rec.setdefault("add_ts", now_ts)
                rec.setdefault("last_modify_ts", now_ts)
                stmt = mysql_insert(model).values(**rec).prefix_with("IGNORE")
                await session.execute(stmt)
                written += 1
        return {"written": written, "message": f"successfully wrote {written} records"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch write failed: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """获取任务完整信息（含 payload 配置）"""
    task = await ConfigService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    profile_name: Optional[str] = None
    profile_id = task.get("profile_id")
    if profile_id:
        profile = await ConfigService.get_profile(profile_id)
        if profile:
            profile_name = profile.get("name")

    return {
        "task_id": task["id"],
        "status": task["status"],
        "payload": task.get("payload_snapshot", {}),
        "payload_snapshot": task.get("payload_snapshot", {}),
        "profile_id": task.get("profile_id"),
        "profile_name": profile_name,
        "error_message": task.get("error_message"),
        "progress": task.get("progress"),
    }


@router.put("/tasks/{task_id}/progress")
async def update_task_progress(task_id: int, body: TaskProgressRequest):
    """更新爬虫进度（首次上报自动将 pending → running）"""
    task = await ConfigService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # 首次上报进度时自动转换状态
    if task.get("status") == "pending":
        await ConfigService.mark_task_running(task_id)

    progress_data = {
        "progress": body.progress,
        "message": body.message,
    }
    await ConfigService.update_task_progress(task_id, progress_data)
    return {"task_id": task_id, "progress": body.progress}


@router.put("/tasks/{task_id}/finish")
async def finish_task(task_id: int, body: TaskFinishRequest):
    """标记任务完成或失败"""
    task = await ConfigService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if body.status not in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {body.status}, must be 'completed', 'failed' or 'cancelled'",
        )

    await ConfigService.mark_task_finished(
        task_id=task_id,
        success=body.status == "completed",
        error_message=body.error if body.error else None,
        status=body.status,
    )

    return {
        "task_id": task_id,
        "status": body.status,
        "total_count": body.total_count,
        "success_count": body.success_count,
    }


# ── Pro: 断点续爬 & 多账号 ──────────────────────────────────────

# 内存中的 checkpoint 存储（本地文件为主，远程为辅）
_checkpoint_store: dict[str, dict] = {}


class CheckpointData(BaseModel):
    task_id: int
    platform: str
    crawler_type: str
    keywords: str = ""
    current_page: int = 1
    crawled_note_ids: list[str] = []
    total_crawled: int = 0
    last_cursor: Optional[str] = None
    last_note_time: Optional[int] = None
    comment_progress: dict[str, int] = {}
    creator_crawled_count: int = 0
    status: str = "running"
    updated_at: float = 0.0


@router.get("/tasks/{task_id}/checkpoint")
async def get_task_checkpoint(task_id: int):
    """获取任务断点数据"""
    key = str(task_id)
    if key in _checkpoint_store:
        return _checkpoint_store[key]
    # 也尝试从 CrawlerTask.progress 字段读取
    task = await ConfigService.get_task(task_id)
    if task and task.get("progress") and isinstance(task["progress"], dict):
        cp = task["progress"]
        if cp.get("status") == "running":
            _checkpoint_store[key] = cp
            return cp
    return {}


@router.put("/tasks/{task_id}/checkpoint")
async def save_task_checkpoint(task_id: int, body: dict):
    """保存任务断点数据"""
    _checkpoint_store[str(task_id)] = body
    # 同时写入 CrawlerTask.progress 字段做持久化
    await ConfigService.update_task_progress(task_id, body)
    return {"status": "ok", "task_id": task_id}


class AccountRequest(BaseModel):
    platform: Optional[str] = None
    status: Optional[str] = "active"


@router.get("/accounts")
async def list_accounts(
    platform: Optional[str] = None,
    status: Optional[str] = "active",
):
    """获取平台账号列表（多账号管理）"""
    try:
        from sqlalchemy import select
        async with get_mysql_session() as session:
            stmt = select(CrawlerAccount)
            if platform:
                stmt = stmt.where(CrawlerAccount.platform == platform)
            if status:
                stmt = stmt.where(CrawlerAccount.status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return {
                "platform": platform,
                "accounts": [
                    {
                        "id": row.id,
                        "platform": row.platform,
                        "username": row.username,
                        "phone": row.phone or "",
                        "cookies": row.cookies or {},
                        "user_agent": row.user_agent or "",
                        "status": row.status,
                        "max_daily_requests": row.max_daily_requests,
                        "daily_request_count": row.daily_request_count,
                        "total_request_count": row.total_request_count,
                    }
                    for row in rows
                ],
            }
    except Exception as e:
        return {"platform": platform, "accounts": [], "error": str(e)}


# ── 爬虫任务日志查询 ──────────────────────────────────────────


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: int,
    level: Optional[str] = Query(None, description="按日志级别过滤: info/warning/error/success/debug"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(50, ge=10, le=500, description="每页条数 (10-500)"),
):
    """查询爬虫任务的持久化运行日志，支持按级别过滤和分页"""
    from sqlalchemy import select, func

    # 验证任务存在，同时获取任务摘要信息
    task = await ConfigService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    payload = task.get("payload_snapshot") or {}
    platform = payload.get("platform", "unknown")
    task_summary = {
        "task_id": task_id,
        "status": task.get("status"),
        "platform": platform,
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
    }

    async with get_mysql_session() as session:
        # 统计总数
        count_stmt = (
            select(func.count())
            .select_from(CrawlerTaskLog)
            .where(CrawlerTaskLog.task_id == task_id)
        )
        if level:
            count_stmt = count_stmt.where(CrawlerTaskLog.level == level)
        total = (await session.execute(count_stmt)).scalar() or 0

        # 获取该任务的所有去重日志级别（用于前端构建过滤 UI）
        levels_stmt = (
            select(CrawlerTaskLog.level)
            .where(CrawlerTaskLog.task_id == task_id)
            .distinct()
        )
        levels_result = await session.execute(levels_stmt)
        levels = sorted([row[0] for row in levels_result.all()])

        # 分页查询日志（按 id 升序，即写入先后顺序）
        offset = (page - 1) * page_size
        logs_stmt = (
            select(CrawlerTaskLog)
            .where(CrawlerTaskLog.task_id == task_id)
        )
        if level:
            logs_stmt = logs_stmt.where(CrawlerTaskLog.level == level)
        logs_stmt = logs_stmt.order_by(CrawlerTaskLog.id.asc()).offset(offset).limit(page_size)

        logs_result = await session.execute(logs_stmt)
        logs = [
            {
                "id": row.id,
                "level": row.level,
                "message": row.message,
                "recorded_at": row.recorded_at,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in logs_result.scalars().all()
        ]

    return {
        "task_id": task_id,
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "levels": levels,
        "task_summary": task_summary,
    }


# ── 爬虫任务日志批量写入 ──────────────────────────────────────


class LogBatchItem(BaseModel):
    task_id: int
    level: str = "info"
    message: str
    recorded_at: str


class LogBatchRequest(BaseModel):
    logs: list[LogBatchItem]


@router.post("/logs/batch")
async def batch_write_logs(body: LogBatchRequest):
    """批量写入爬虫任务运行日志到 MySQL"""
    if not body.logs:
        return {"ok": True, "count": 0}

    try:
        from sqlalchemy import insert
        async with get_mysql_session() as session:
            stmt = insert(CrawlerTaskLog).values([
                {
                    "task_id": log.task_id,
                    "level": log.level,
                    "message": log.message,
                    "recorded_at": log.recorded_at,
                }
                for log in body.logs
            ])
            await session.execute(stmt)
        return {"ok": True, "count": len(body.logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch log write failed: {str(e)}")
