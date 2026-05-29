# -*- coding: utf-8 -*-
"""
评论爬取执行器

支持同步/异步/批量三种模式，集成风控限流。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from .rate_limiter import rate_limiter

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


@dataclass
class CommentTask:
    task_id: str
    platform: str
    post_id: str
    post_url: str
    max_comments: int
    crawl_replies: bool
    status: str = "pending"
    progress: int = 0
    total_crawled: int = 0
    comments: List[Dict] = field(default_factory=list)
    error: str = ""
    created_at: str = ""
    finished_at: str = ""


class CommentExecutor:
    """评论爬取执行器 — 单个帖子评论采集"""

    def __init__(self):
        self._tasks: Dict[str, CommentTask] = {}
        self._lock = asyncio.Lock()

    async def execute_sync(
        self, platform: str, post_id: str, post_url: str = "",
        max_comments: int = 50, crawl_replies: bool = False,
    ) -> Dict[str, Any]:
        """同步模式：等待完成并返回结果"""
        task_id = str(uuid.uuid4())[:8]
        task = CommentTask(
            task_id=task_id, platform=platform, post_id=post_id,
            post_url=post_url, max_comments=max_comments,
            crawl_replies=crawl_replies, status="running",
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        self._tasks[task_id] = task

        try:
            comments = await self._do_crawl(task)
            task.status = "completed"
            task.comments = comments
            task.total_crawled = len(comments)
            task.finished_at = datetime.now().strftime("%H:%M:%S")
            return {"status": "completed", "task_id": task_id, "total": len(comments), "comments": comments[:20]}
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.finished_at = datetime.now().strftime("%H:%M:%S")
            return {"status": "failed", "task_id": task_id, "error": str(e)}

    async def execute_async(
        self, platform: str, post_id: str, post_url: str = "",
        max_comments: int = 50, crawl_replies: bool = False,
    ) -> Dict[str, Any]:
        """异步模式：提交后立即返回 task_id"""
        task_id = str(uuid.uuid4())[:8]
        task = CommentTask(
            task_id=task_id, platform=platform, post_id=post_id,
            post_url=post_url, max_comments=max_comments,
            crawl_replies=crawl_replies, status="queued",
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        self._tasks[task_id] = task

        asyncio.create_task(self._run_async(task))
        return {"status": "queued", "task_id": task_id}

    async def execute_batch(
        self, platform: str, posts: List[Dict[str, str]],
        max_comments: int = 50, crawl_replies: bool = False,
    ) -> Dict[str, Any]:
        """批量异步模式：多个帖子同时提交"""
        task_ids = []
        for post in posts:
            post_id = post.get("post_id", "")
            post_url = post.get("post_url", "")
            if not post_id and not post_url:
                continue
            result = await self.execute_async(
                platform=platform, post_id=post_id, post_url=post_url,
                max_comments=max_comments, crawl_replies=crawl_replies,
            )
            task_ids.append(result["task_id"])
        return {"status": "batch_queued", "platform": platform, "count": len(task_ids), "task_ids": task_ids}

    async def _run_async(self, task: CommentTask) -> None:
        task.status = "running"
        try:
            comments = await self._do_crawl(task)
            task.comments = comments
            task.total_crawled = len(comments)
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        task.finished_at = datetime.now().strftime("%H:%M:%S")

    async def _do_crawl(self, task: CommentTask) -> List[Dict]:
        """核心爬取逻辑 — 调用平台API逐页爬取评论"""
        platform = task.platform

        # 风控：获取并发槽位
        await rate_limiter.acquire_slot(platform)
        try:
            comments: List[Dict] = []

            try:
                from main import CrawlerFactory
                crawler = CrawlerFactory.create_crawler(platform=platform)
            except Exception as e:
                return await self._crawl_via_http(task)

            browser_ctx = None
            try:
                try:
                    browser_ctx = await crawler.launch_browser(
                        chromium=None, playwright_proxy=None,
                        user_agent=None, headless=True,
                    )
                    await crawler.login()
                except Exception as e:
                    return await self._crawl_via_http(task)

                # 获取评论 — 通过平台 API Client
                api_client = getattr(crawler, f"{platform}_client", None)
                if api_client is None:
                    raise RuntimeError(f"不支持的平台或缺少 API Client: {platform}")

                # 使用现有评论API逐页爬取
                collected = []
                comments_cursor = ""
                has_more = True
                page = 0

                while has_more and len(collected) < task.max_comments:
                    page += 1
                    task.progress = page

                    # 风控：获取令牌
                    await rate_limiter.acquire(platform)

                    # 平台随机延迟
                    import random
                    await asyncio.sleep(random.uniform(0.5, 2.0))

                    # 调用平台评论API (以小红书为例)
                    if platform == "xhs" and hasattr(api_client, 'get_note_comments'):
                        note_id = task.post_id
                        xsec_token = ""
                        if "xsec_token=" in task.post_url:
                            xsec_token = task.post_url.split("xsec_token=")[-1].split("&")[0]

                        resp = await api_client.get_note_comments(
                            note_id=note_id, cursor=comments_cursor,
                            xsec_token=xsec_token,
                        )
                        comments_data = resp.get("data", {}).get("comments", [])
                        has_more = resp.get("data", {}).get("has_more", False)
                        comments_cursor = resp.get("data", {}).get("cursor", "")
                        for c in comments_data:
                            collected.append({
                                "comment_id": c.get("id", ""),
                                "content": c.get("content", ""),
                                "user_name": c.get("user_info", {}).get("nickname", ""),
                                "like_count": c.get("like_count", 0),
                                "sub_comment_count": c.get("sub_comment_count", 0),
                                "create_time": c.get("create_time", 0),
                            })
                    elif platform in ("dy", "douyin") and hasattr(api_client, 'get_aweme_comments'):
                        resp = await api_client.get_aweme_comments(
                            aweme_id=task.post_id,
                            cursor=int(comments_cursor or "0"),
                        )
                        comments_data = resp.get("comments", [])
                        has_more = bool(resp.get("has_more", 0))
                        comments_cursor = str(resp.get("cursor", 0))
                        for c in comments_data:
                            collected.append({
                                "comment_id": c.get("cid", ""),
                                "content": c.get("text", ""),
                                "user_name": c.get("user", {}).get("nickname", ""),
                                "like_count": c.get("digg_count", 0),
                                "sub_comment_count": c.get("reply_comment_total", 0),
                                "create_time": c.get("create_time", 0),
                            })
                    else:
                        # 回退：尝试 HTTP 采集
                        return await self._crawl_via_http(task)

                    if not has_more and comments_cursor == "" and page == 1:
                        has_more = False  # 仅一页

                comments = collected

            finally:
                if browser_ctx:
                    try:
                        await browser_ctx.close()
                    except Exception:
                        pass

            return comments

        finally:
            rate_limiter.release_slot(platform)

    async def _crawl_via_http(self, task: CommentTask) -> List[Dict]:
        """简化模式：通过 Data-API 查询已存储的评论"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{DATA_API_URL}/api/data/db/{task.platform}/comment",
                    params={"task_id": 0, "page": 1, "page_size": task.max_comments},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    return [
                        {"comment_id": item.get("comment_id", ""), "content": item.get("content", "")}
                        for item in items[:task.max_comments]
                    ]
        except Exception:
            pass
        return []

    def get_task(self, task_id: str) -> Optional[CommentTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[CommentTask]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


# 全局实例
comment_executor = CommentExecutor()
