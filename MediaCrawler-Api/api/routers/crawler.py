# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/crawler.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from fastapi import APIRouter, HTTPException, Query

from ..schemas import CrawlerStartRequest, CrawlerStatusResponse
from ..schemas.config_mgmt import TaskResponse
from ..services import crawler_manager

router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.post("/start")
async def start_crawler(request: CrawlerStartRequest):
    """Start crawler task"""
    success = await crawler_manager.start(request)
    if not success:
        if crawler_manager.process and crawler_manager.process.poll() is None:
            raise HTTPException(status_code=400, detail="Crawler is already running")
        raise HTTPException(status_code=500, detail="Failed to start crawler")

    return {
        "status": "ok",
        "message": "Crawler started successfully",
        "task_id": crawler_manager.current_task_id,
    }


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
):
    from services.config_service import ConfigService

    return await ConfigService.list_tasks_paginated(page=page, page_size=page_size, status=status)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_detail(task_id: int):
    from services.config_service import ConfigService

    task = await ConfigService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/tasks/{task_id}/rerun")
async def rerun_task(task_id: int):
    from services.config_service import ConfigService

    original = await ConfigService.get_task(task_id)
    if not original:
        raise HTTPException(status_code=404, detail="任务不存在")

    if crawler_manager.process and crawler_manager.process.poll() is None:
        raise HTTPException(status_code=400, detail="爬虫正在运行中，请先停止当前任务")

    p = original["payload_snapshot"]
    start_request = CrawlerStartRequest(
        profile_id=original.get("profile_id"),
        platform=p["platform"],
        login_type=p.get("login_type", "qrcode"),
        crawler_type=p.get("crawler_type", "search"),
        keywords=p.get("keywords", ""),
        specified_ids=p.get("specified_ids", ""),
        creator_ids=p.get("creator_ids", ""),
        start_page=p.get("start_page", 1),
        enable_comments=p.get("enable_comments", True),
        enable_sub_comments=p.get("enable_sub_comments", False),
        cookies=p.get("cookies", ""),
        headless=p.get("headless", False),
    )

    success = await crawler_manager.start(start_request)
    if not success:
        raise HTTPException(status_code=500, detail="启动失败")

    return {
        "status": "ok",
        "message": "任务已重新启动",
        "task_id": crawler_manager.current_task_id,
        "original_task_id": task_id,
    }


@router.post("/stop")
async def stop_crawler():
    """Stop crawler task"""
    success = await crawler_manager.stop()
    if not success:
        if not crawler_manager.process or crawler_manager.process.poll() is not None:
            raise HTTPException(status_code=400, detail="No crawler is running")
        raise HTTPException(status_code=500, detail="Failed to stop crawler")

    return {"status": "ok", "message": "Crawler stopped successfully"}


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status():
    """Get crawler status"""
    return crawler_manager.get_status()


@router.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent logs"""
    logs = crawler_manager.logs[-limit:] if limit > 0 else crawler_manager.logs
    return {"logs": [log.model_dump() for log in logs]}
