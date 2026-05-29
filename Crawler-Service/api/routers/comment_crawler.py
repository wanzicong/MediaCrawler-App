# -*- coding: utf-8 -*-
"""
评论爬取 & 任务管道 API 路由

端点:
- /api/crawler-pro/comments/sync|async|batch
- /api/crawler-pro/comments/tasks
- /api/crawler-pro/comments/rate-limit-status
- /api/crawler-pro/pipelines CRUD + run/stop
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from engine.comment_executor import comment_executor
from engine.pipeline_executor import pipeline_executor, PipelineMode
from engine.rate_limiter import rate_limiter

router = APIRouter(prefix="/crawler-pro", tags=["comment-crawler"])


# ==================== 请求模型 ====================

class CommentSyncRequest(BaseModel):
    platform: str
    post_id: str = ""
    post_url: str = ""
    max_comments: int = 50
    crawl_replies: bool = False


class CommentAsyncRequest(BaseModel):
    platform: str
    post_id: str = ""
    post_url: str = ""
    max_comments: int = 50
    crawl_replies: bool = False
    priority: str = "normal"


class CommentBatchRequest(BaseModel):
    platform: str
    posts: List[dict]
    max_comments: int = 50
    crawl_replies: bool = False


class PipelineCreateRequest(BaseModel):
    name: str
    platform: str
    keywords: List[str]
    mode: str = "batch"  # batch | queue | cron
    config: Optional[dict] = None


# ==================== 评论爬取端点 ====================

@router.post("/comments/sync")
async def comment_sync(body: CommentSyncRequest):
    """同步爬取单个帖子评论 (等待完成返回结果)"""
    result = await comment_executor.execute_sync(
        platform=body.platform,
        post_id=body.post_id,
        post_url=body.post_url,
        max_comments=body.max_comments,
        crawl_replies=body.crawl_replies,
    )
    return result


@router.post("/comments/async")
async def comment_async(body: CommentAsyncRequest):
    """异步爬取单个帖子评论 (返回 task_id 即可轮询)"""
    result = await comment_executor.execute_async(
        platform=body.platform,
        post_id=body.post_id,
        post_url=body.post_url,
        max_comments=body.max_comments,
        crawl_replies=body.crawl_replies,
    )
    return result


@router.post("/comments/batch")
async def comment_batch(body: CommentBatchRequest):
    """批量异步爬取多个帖子的评论"""
    result = await comment_executor.execute_batch(
        platform=body.platform,
        posts=body.posts,
        max_comments=body.max_comments,
        crawl_replies=body.crawl_replies,
    )
    return result


@router.get("/comments/tasks")
async def list_comment_tasks(limit: int = Query(50, le=200)):
    """评论任务列表"""
    tasks = comment_executor.list_tasks(limit=limit)
    return {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id, "platform": t.platform,
                "post_id": t.post_id, "status": t.status,
                "progress": t.progress, "total_crawled": t.total_crawled,
                "error": t.error, "created_at": t.created_at,
                "finished_at": t.finished_at,
            }
            for t in tasks
        ],
    }


@router.get("/comments/tasks/{task_id}")
async def get_comment_task(task_id: str):
    """评论任务详情"""
    task = comment_executor.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {
        "task_id": task.task_id, "platform": task.platform,
        "post_id": task.post_id, "post_url": task.post_url,
        "max_comments": task.max_comments, "crawl_replies": task.crawl_replies,
        "status": task.status, "progress": task.progress,
        "total_crawled": task.total_crawled,
        "comments": task.comments[:50],
        "error": task.error, "created_at": task.created_at,
        "finished_at": task.finished_at,
    }


@router.delete("/comments/tasks/{task_id}")
async def delete_comment_task(task_id: str):
    """取消/删除评论任务"""
    ok = comment_executor.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"status": "ok", "message": "任务已删除"}


@router.get("/comments/rate-limit-status")
async def get_rate_limit_status():
    """各平台限流状态"""
    return rate_limiter.get_status()


# ==================== 任务管道端点 ====================

@router.post("/pipelines")
async def create_pipeline(body: PipelineCreateRequest):
    """创建任务管道"""
    mode = PipelineMode(body.mode) if body.mode in [m.value for m in PipelineMode] else PipelineMode.BATCH
    pipeline = await pipeline_executor.create(
        name=body.name, platform=body.platform,
        keywords=body.keywords, mode=mode, config=body.config,
    )
    return {
        "status": "ok", "pipeline_id": pipeline.pipeline_id,
        "name": pipeline.name, "platform": pipeline.platform,
        "keywords_count": len(pipeline.keywords), "mode": pipeline.mode.value,
    }


@router.get("/pipelines")
async def list_pipelines():
    """管道列表"""
    pipelines = pipeline_executor.list_all()
    return {
        "pipelines": [
            {
                "pipeline_id": p.pipeline_id, "name": p.name,
                "platform": p.platform, "keywords_count": len(p.keywords),
                "mode": p.mode.value, "status": p.status,
                "progress": p.progress, "total": p.total,
                "created_at": p.created_at,
            }
            for p in pipelines
        ],
    }


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """管道详情"""
    p = pipeline_executor.get(pipeline_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"管道 {pipeline_id} 不存在")
    return {
        "pipeline_id": p.pipeline_id, "name": p.name,
        "platform": p.platform, "mode": p.mode.value,
        "status": p.status, "progress": p.progress, "total": p.total,
        "created_at": p.created_at,
        "tasks": [
            {"ref": t.task_ref, "keyword": t.keyword, "status": t.status,
             "task_id": t.task_id, "error": t.error}
            for t in p.tasks
        ],
    }


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str):
    """执行管道"""
    result = await pipeline_executor.run(pipeline_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pipelines/{pipeline_id}/stop")
async def stop_pipeline(pipeline_id: str):
    """停止管道"""
    ok = await pipeline_executor.stop(pipeline_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"管道 {pipeline_id} 不存在")
    return {"status": "ok", "message": "管道已停止"}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """删除管道"""
    ok = pipeline_executor.delete(pipeline_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"管道 {pipeline_id} 不存在或正在运行")
    return {"status": "ok", "message": "管道已删除"}
