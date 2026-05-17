# -*- coding: utf-8 -*-
"""从 MySQL 业务表分页查询爬取数据"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import delete, func, select

from database.db_session import get_mysql_session
from database.models import (
    BilibiliVideo,
    BilibiliVideoComment,
    DouyinAweme,
    DouyinAwemeComment,
    KuaishouVideo,
    KuaishouVideoComment,
    WeiboNote,
    WeiboNoteComment,
    XhsCreator,
    XhsNote,
    XhsNoteComment,
    TiebaNote,
    TiebaComment,
    ZhihuContent,
    ZhihuComment,
)

PLATFORM_META = {
    "xhs": {
        "label": "小红书",
        "icon": "book-open",
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": XhsNote, "label": "笔记"},
            "comments": {"model": XhsNoteComment, "label": "评论"},
            "creators": {"model": XhsCreator, "label": "创作者"},
        },
    },
    "dy": {
        "label": "抖音",
        "icon": "music",
        "content_id_field": "aweme_id",
        "kinds": {
            "contents": {"model": DouyinAweme, "label": "视频"},
            "comments": {"model": DouyinAwemeComment, "label": "评论"},
        },
    },
    "ks": {
        "label": "快手",
        "icon": "video",
        "content_id_field": "video_id",
        "kinds": {
            "contents": {"model": KuaishouVideo, "label": "视频"},
            "comments": {"model": KuaishouVideoComment, "label": "评论"},
        },
    },
    "bili": {
        "label": "B站",
        "icon": "tv",
        "content_id_field": "video_id",
        "kinds": {
            "contents": {"model": BilibiliVideo, "label": "视频"},
            "comments": {"model": BilibiliVideoComment, "label": "评论"},
        },
    },
    "wb": {
        "label": "微博",
        "icon": "message-circle",
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": WeiboNote, "label": "微博"},
            "comments": {"model": WeiboNoteComment, "label": "评论"},
        },
    },
    "tieba": {
        "label": "贴吧",
        "icon": "messages-square",
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": TiebaNote, "label": "帖子"},
            "comments": {"model": TiebaComment, "label": "评论"},
        },
    },
    "zhihu": {
        "label": "知乎",
        "icon": "help-circle",
        "content_id_field": "content_id",
        "kinds": {
            "contents": {"model": ZhihuContent, "label": "内容"},
            "comments": {"model": ZhihuComment, "label": "评论"},
        },
    },
}


def list_platforms() -> list[dict]:
    return [
        {
            "value": key,
            "label": meta["label"],
            "icon": meta.get("icon", ""),
            "kinds": [
                {"value": k, "label": v["label"]} for k, v in meta["kinds"].items()
            ],
        }
        for key, meta in PLATFORM_META.items()
    ]


JS_MAX_SAFE_INTEGER = 9007199254740991


def _row_to_dict(row: Any) -> dict:
    data = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        # 超大整数转字符串，避免 JavaScript 解析 JSON 时丢失精度
        # (如抖音 aweme_id 可达 7.6e18，远超 JS Number.MAX_SAFE_INTEGER 9e15)
        if isinstance(val, int) and not isinstance(val, bool) and abs(val) > JS_MAX_SAFE_INTEGER:
            val = str(val)
        data[col.name] = val
    return data


class DataQueryService:
    @staticmethod
    async def query(
        platform: str,
        kind: str,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        content_id: Optional[str] = None,
    ) -> dict:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        kind_meta = meta["kinds"].get(kind)
        if not kind_meta:
            raise ValueError(f"不支持的数据类型: {kind}")

        model = kind_meta["model"]
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        async with get_mysql_session() as session:
            count_stmt = select(func.count()).select_from(model)
            list_stmt = select(model).order_by(model.id.desc()).offset(offset).limit(page_size)

            if content_id and kind == "contents":
                cid_field = meta["content_id_field"]
                if hasattr(model, cid_field):
                    col = getattr(model, cid_field)
                    count_stmt = count_stmt.where(col == content_id)
                    list_stmt = list_stmt.where(col == content_id)

            if keyword:
                pattern = f"%{keyword}%"
                if hasattr(model, "title"):
                    count_stmt = count_stmt.where(model.title.like(pattern))
                    list_stmt = list_stmt.where(model.title.like(pattern))
                elif hasattr(model, "content_text"):
                    count_stmt = count_stmt.where(model.content_text.like(pattern))
                    list_stmt = list_stmt.where(model.content_text.like(pattern))
                elif hasattr(model, "content"):
                    count_stmt = count_stmt.where(model.content.like(pattern))
                    list_stmt = list_stmt.where(model.content.like(pattern))

            total = (await session.execute(count_stmt)).scalar() or 0
            rows = (await session.execute(list_stmt)).scalars().all()

        return {
            "platform": platform,
            "kind": kind,
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def query_by_task(
        platform: str,
        task_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        model = meta["kinds"]["contents"]["model"]
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        async with get_mysql_session() as session:
            count_stmt = select(func.count()).select_from(model).where(model.task_id == task_id)
            list_stmt = (
                select(model)
                .where(model.task_id == task_id)
                .order_by(model.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            total = (await session.execute(count_stmt)).scalar() or 0
            rows = (await session.execute(list_stmt)).scalars().all()

        return {
            "platform": platform,
            "kind": "contents",
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def query_comments_by_content(
        platform: str,
        content_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        comment_model = meta["kinds"]["comments"]["model"]
        content_id_field = meta["content_id_field"]
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        async with get_mysql_session() as session:
            col = getattr(comment_model, content_id_field)
            count_stmt = select(func.count()).select_from(comment_model).where(col == content_id)
            list_stmt = (
                select(comment_model)
                .where(col == content_id)
                .order_by(comment_model.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            total = (await session.execute(count_stmt)).scalar() or 0
            rows = (await session.execute(list_stmt)).scalars().all()

        return {
            "platform": platform,
            "kind": "comments",
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def delete_record(platform: str, kind: str, record_id: int) -> bool:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        kind_meta = meta["kinds"].get(kind)
        if not kind_meta:
            raise ValueError(f"不支持的数据类型: {kind}")
        model = kind_meta["model"]

        async with get_mysql_session() as session:
            record = await session.get(model, record_id)
            if not record:
                return False
            await session.delete(record)
            return True

    @staticmethod
    async def delete_by_task(platform: str, task_id: int) -> dict:
        """删除某任务下的所有内容和评论，返回删除计数"""
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        deleted_counts = {"contents": 0, "comments": 0}

        async with get_mysql_session() as session:
            content_model = meta["kinds"]["contents"]["model"]
            comment_model = meta["kinds"]["comments"]["model"]
            content_id_field = meta["content_id_field"]

            # 先查该任务下的所有内容ID
            content_ids_result = await session.execute(
                select(getattr(content_model, content_id_field)).where(content_model.task_id == task_id)
            )
            content_ids = [row[0] for row in content_ids_result.all() if row[0]]

            # 删除评论
            if content_ids and hasattr(comment_model, content_id_field):
                col = getattr(comment_model, content_id_field)
                result = await session.execute(
                    delete(comment_model).where(col.in_(content_ids))
                )
                deleted_counts["comments"] = result.rowcount or 0

            # 删除内容
            result = await session.execute(
                delete(content_model).where(content_model.task_id == task_id)
            )
            deleted_counts["contents"] = result.rowcount or 0

        return deleted_counts

    @staticmethod
    async def get_task_data_stats(task_id: int) -> dict:
        """统计某任务在各平台产生的数据量"""
        platform_stats = {}
        total_contents = 0
        total_comments = 0

        async with get_mysql_session() as session:
            for key, meta in PLATFORM_META.items():
                content_model = meta["kinds"]["contents"]["model"]
                # 统计内容数
                content_count = (
                    await session.execute(
                        select(func.count()).select_from(content_model).where(content_model.task_id == task_id)
                    )
                ).scalar() or 0
                total_contents += content_count

                # 统计评论数：查该任务内容下的所有评论
                comment_count = 0
                if content_count > 0:
                    comment_model = meta["kinds"]["comments"]["model"]
                    content_id_field = meta["content_id_field"]
                    content_ids_result = await session.execute(
                        select(getattr(content_model, content_id_field)).where(content_model.task_id == task_id)
                    )
                    content_ids = [row[0] for row in content_ids_result.all() if row[0]]
                    if content_ids and hasattr(comment_model, content_id_field):
                        col = getattr(comment_model, content_id_field)
                        comment_count = (
                            await session.execute(
                                select(func.count()).select_from(comment_model).where(col.in_(content_ids))
                            )
                        ).scalar() or 0
                total_comments += comment_count

                if content_count > 0 or comment_count > 0:
                    platform_stats[key] = {
                        "label": meta["label"],
                        "contents": content_count,
                        "comments": comment_count,
                    }

        return {
            "task_id": task_id,
            "platforms": platform_stats,
            "total_contents": total_contents,
            "total_comments": total_comments,
        }
