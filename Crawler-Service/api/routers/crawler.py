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

import os

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..schemas import CrawlerStartRequest, CrawlerStatusResponse
from ..schemas.config_mgmt import TaskResponse
from ..services import crawler_manager

router = APIRouter(prefix="/crawler", tags=["crawler"])
DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


@router.post("/start")
async def start_crawler(request: CrawlerStartRequest):
    """Start crawler task"""
    result = await crawler_manager.start(request)
    if result.get("started"):
        return {
            "status": "ok",
            "message": "爬虫已启动",
            "task_id": result["task_id"],
        }
    if result.get("queued"):
        return {
            "status": "ok",
            "message": f"爬虫正忙，任务已加入队列（位置 {result['queue_position']}）",
            "task_id": result["task_id"],
            "queued": True,
            "queue_position": result["queue_position"],
        }
    raise HTTPException(status_code=500, detail=result.get("error", "启动失败"))


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    platform: str = Query(None),
):
    params = {"page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if platform:
        params["platform"] = platform
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DATA_API_URL}/api/internal/tasks", params=params)
        resp.raise_for_status()
        return resp.json()


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_detail(task_id: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="任务不存在")
        resp.raise_for_status()
        return resp.json()


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: int):
    """执行一个待执行（pending）的任务"""
    result = await crawler_manager.execute_task(task_id)
    if result.get("started"):
        return {
            "status": "ok",
            "message": f"任务 #{task_id} 已开始执行",
            "task_id": task_id,
        }
    raise HTTPException(status_code=400, detail=result.get("error", "执行失败"))


@router.post("/tasks/{task_id}/rerun")
async def rerun_task(task_id: int, resume: bool = True):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="任务不存在")
        resp.raise_for_status()
        original = resp.json()

    p = dict(original.get("payload", original.get("payload_snapshot", {})))
    start_page = p.get("start_page", 1)

    # 断点续爬：从上次进度恢复
    if resume and original.get("progress"):
        progress = original["progress"]
        if progress.get("page") and progress["page"] > start_page:
            start_page = progress["page"]
        if progress.get("keyword"):
            p["keywords"] = progress["keyword"]

    start_request = CrawlerStartRequest(
        profile_id=original.get("profile_id"),
        platform=p["platform"],
        login_type=p.get("login_type", "qrcode"),
        crawler_type=p.get("crawler_type", "search"),
        keywords=p.get("keywords", ""),
        specified_ids=p.get("specified_ids", ""),
        creator_ids=p.get("creator_ids", ""),
        start_page=start_page,
        enable_comments=p.get("enable_comments", True),
        enable_sub_comments=p.get("enable_sub_comments", False),
        cookies=p.get("cookies", ""),
        headless=p.get("headless", False),
    )

    result = await crawler_manager.start(start_request)
    if result.get("started"):
        return {
            "status": "ok",
            "message": "任务已重新启动" + (f"（从第 {start_page} 页续爬）" if resume and start_page > 1 else ""),
            "task_id": result["task_id"],
            "original_task_id": task_id,
        }
    if result.get("queued"):
        return {
            "status": "ok",
            "message": f"爬虫正忙，任务已加入队列（位置 {result['queue_position']}）",
            "task_id": result["task_id"],
            "original_task_id": task_id,
            "queued": True,
            "queue_position": result["queue_position"],
        }
    raise HTTPException(status_code=500, detail=result.get("error", "启动失败"))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除任务记录"""
    # 先检查任务状态
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="任务不存在")
        resp.raise_for_status()
        task = resp.json()

    if task.get("status") == "running":
        raise HTTPException(status_code=400, detail="无法删除正在运行的任务，请先停止爬虫")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="任务不存在")
        resp.raise_for_status()
        return {"status": "ok", "message": "任务已删除"}


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


@router.post("/cleanup-zombies")
async def cleanup_zombie_processes():
    """强制清理僵尸浏览器进程和端口占用"""
    import os
    import subprocess
    import sys

    killed_processes = []
    freed_ports = []

    # Windows: kill Edge/Chrome processes and check debug ports
    if sys.platform == "win32":
        # 1. Kill stuck msedge/chrome processes
        for proc_name in ["msedge.exe", "chrome.exe"]:
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", proc_name],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    killed_processes.append(proc_name)
            except Exception:
                pass

        # 2. Free debug ports 9222-9230
        for port in range(9222, 9230):
            try:
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.splitlines():
                    if f"127.0.0.1:{port}" in line and "LISTENING" in line:
                        parts = line.strip().split()
                        pid = parts[-1]
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True, timeout=5,
                        )
                        freed_ports.append(port)
            except Exception:
                pass

    # Linux/Mac: kill chrome/edge processes
    else:
        for proc_name in ["chromium", "chrome", "edge", "msedge"]:
            try:
                result = subprocess.run(
                    ["pkill", "-9", "-f", proc_name],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    killed_processes.append(proc_name)
            except Exception:
                pass

    # Also clean up any orphaned Python subprocess with --task-id
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["wmic", "process", "where", "commandline like '%--task-id%'", "delete"],
                capture_output=True, timeout=10,
            )
    except Exception:
        pass

    return {
        "status": "ok",
        "message": "僵尸进程清理完成",
        "killed_processes": killed_processes,
        "freed_ports": freed_ports,
    }
