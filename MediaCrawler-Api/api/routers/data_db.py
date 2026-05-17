# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.data_query_service import DataQueryService, list_platforms

router = APIRouter(prefix="/data/db", tags=["data-db"])


@router.get("/platforms")
async def get_db_platforms():
    return {"platforms": list_platforms()}


@router.get("/task/{task_id}/stats")
async def get_task_data_stats(task_id: int):
    """获取任务的数据统计（各平台内容/评论数量）"""
    try:
        return await DataQueryService.get_task_data_stats(task_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{platform}/task/{task_id}")
async def query_data_by_task(
    platform: str,
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """按任务 ID 查询该平台爬取的内容数据"""
    try:
        return await DataQueryService.query_by_task(platform, task_id, page, page_size)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{platform}/{kind}/content/{content_id}")
async def query_comments_by_content(
    platform: str,
    kind: str,
    content_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """按内容 ID 查询该内容下的评论"""
    if kind != "comments":
        raise HTTPException(400, "kind 必须为 'comments'，此端点仅用于查询评论")
    try:
        return await DataQueryService.query_comments_by_content(platform, content_id, page, page_size)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{platform}/{kind}/{record_id}")
async def delete_data_record(
    platform: str,
    kind: str,
    record_id: int,
):
    """删除单条数据记录"""
    try:
        deleted = await DataQueryService.delete_record(platform, kind, record_id)
        if not deleted:
            raise HTTPException(404, "记录不存在")
        return {"status": "ok", "message": "记录已删除"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{platform}/{kind}")
async def query_data(
    platform: str,
    kind: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    content_id: Optional[str] = None,
):
    try:
        return await DataQueryService.query(platform, kind, page, page_size, keyword, content_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
