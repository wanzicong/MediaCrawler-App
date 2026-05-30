# -*- coding: utf-8 -*-
"""从 MySQL 业务表分页查询爬取数据"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import delete, func, select, desc, asc, cast, Integer

from database.db_session import get_mysql_session
from database.models import (
    BilibiliUpInfo,
    BilibiliVideo,
    BilibiliVideoComment,
    DouyinAweme,
    DouyinAwemeComment,
    DyCreator,
    KuaishouVideo,
    KuaishouVideoComment,
    TiebaCreator,
    TiebaNote,
    TiebaComment,
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

# ── 平台元数据缓存（应用启动时从 DB 加载，结构同旧 PLATFORM_META） ──
PLATFORM_META: dict = {}


async def init_platform_meta():
    """从数据库加载已启用平台并合并模型配置，填充 PLATFORM_META 缓存"""
    from services.platform_service import PlatformService

    global PLATFORM_META
    new_meta = await PlatformService.get_platform_meta()
    PLATFORM_META.clear()
    PLATFORM_META.update(new_meta)


def list_platforms() -> list[dict]:
    """
    获取前端下拉框所需的平台列表。
    仅返回缓存中存在的平台（即已启用且已配置模型映射的平台），按 sort_order 排序。
    """
    items = [
        {
            "value": key,
            "label": meta["label"],
            "icon": meta.get("icon", ""),
            "kinds": [
                {"value": k, "label": v["label"]} for k, v in meta["kinds"].items()
            ],
            "sort_order": meta.get("sort_order", 0),
        }
        for key, meta in PLATFORM_META.items()
    ]
    items.sort(key=lambda x: x["sort_order"])
    return items


JS_MAX_SAFE_INTEGER = 9007199254740991

# 创作者各平台的粉丝字段映射（用于默认排序和 _NUMERIC_SORT_FIELDS 中识别）
_CREATOR_FAN_FIELD: dict[str, str] = {
    "xhs": "fans",
    "dy": "fans",
    "wb": "fans",
    "tieba": "fans",
    "bili": "total_fans",
    "zhihu": "fans",
}


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
        order_by: Optional[str] = None,
        order_direction: str = "desc",
        task_id: Optional[int] = None,
    ) -> dict:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        kind_meta = meta["kinds"].get(kind)
        if not kind_meta:
            raise ValueError(f"不支持的数据类型: {kind}")

        model = kind_meta["model"]
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        offset = (page - 1) * page_size

        # 数据库中数字字段可能是 Text 类型，需 CAST 后再排序
        _NUMERIC_SORT_FIELDS = {
            "video_play_count", "video_comment", "video_danmaku", "video_favorite_count",
            "video_share_count", "video_coin_count", "viewd_count", "comment_count",
            "share_count", "collected_count", "liked_count", "disliked_count",
            "like_count", "sub_comment_count", "total_fans", "total_liked",
            "fans", "follows", "interaction",
        }

        order_cols = []
        if order_by and hasattr(model, order_by):
            col = getattr(model, order_by)
            if order_by in _NUMERIC_SORT_FIELDS:
                col = cast(col, Integer)
            order_cols.append(desc(col) if order_direction == "desc" else asc(col))
        # 创作者默认按粉丝数降序排列
        if kind == "creators" and not order_by:
            fan_field = _CREATOR_FAN_FIELD.get(platform)
            if fan_field and hasattr(model, fan_field):
                col = getattr(model, fan_field)
                if fan_field in _NUMERIC_SORT_FIELDS:
                    col = cast(col, Integer)
                order_cols.append(desc(col))
        order_cols.append(model.id.desc())

        async with get_mysql_session() as session:
            count_stmt = select(func.count()).select_from(model)
            list_stmt = select(model).order_by(*order_cols).offset(offset).limit(page_size)

            # 创作者去重：保留每个 user_id 的最新记录（id 最大）
            if kind == "creators" and hasattr(model, "user_id"):
                subq = select(func.max(model.id)).group_by(model.user_id)
                count_stmt = count_stmt.where(model.id.in_(subq))
                list_stmt = list_stmt.where(model.id.in_(subq))

            if content_id and kind == "contents":
                cid_field = meta["content_id_field"]
                if hasattr(model, cid_field):
                    col = getattr(model, cid_field)
                    count_stmt = count_stmt.where(col == content_id)
                    list_stmt = list_stmt.where(col == content_id)

            if keyword:
                pattern = f"%{keyword}%"
                if kind == "creators":
                    if hasattr(model, "nickname"):
                        count_stmt = count_stmt.where(model.nickname.like(pattern))
                        list_stmt = list_stmt.where(model.nickname.like(pattern))
                    elif hasattr(model, "user_nickname"):
                        count_stmt = count_stmt.where(model.user_nickname.like(pattern))
                        list_stmt = list_stmt.where(model.user_nickname.like(pattern))
                elif hasattr(model, "title"):
                    count_stmt = count_stmt.where(model.title.like(pattern))
                    list_stmt = list_stmt.where(model.title.like(pattern))
                elif hasattr(model, "content_text"):
                    count_stmt = count_stmt.where(model.content_text.like(pattern))
                    list_stmt = list_stmt.where(model.content_text.like(pattern))
                elif hasattr(model, "content"):
                    count_stmt = count_stmt.where(model.content.like(pattern))
                    list_stmt = list_stmt.where(model.content.like(pattern))

            if task_id is not None and hasattr(model, "task_id"):
                count_stmt = count_stmt.where(model.task_id == task_id)
                list_stmt = list_stmt.where(model.task_id == task_id)

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
        order_by: Optional[str] = None,
        order_direction: str = "desc",
    ) -> dict:
        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        model = meta["kinds"]["contents"]["model"]
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        offset = (page - 1) * page_size

        # 排序字段（与通用 query 方法一致的 CAST 逻辑）
        _NUMERIC_SORT_FIELDS = {
            "video_play_count", "video_comment", "video_danmaku", "video_favorite_count",
            "video_share_count", "video_coin_count", "viewd_count", "comment_count",
            "share_count", "collected_count", "liked_count", "disliked_count",
            "like_count", "sub_comment_count",
        }
        order_cols = []
        if order_by and hasattr(model, order_by):
            col = getattr(model, order_by)
            if order_by in _NUMERIC_SORT_FIELDS:
                col = cast(col, Integer)
            order_cols.append(desc(col) if order_direction == "desc" else asc(col))
        order_cols.append(model.id.desc())

        async with get_mysql_session() as session:
            count_stmt = select(func.count()).select_from(model).where(model.task_id == task_id)
            list_stmt = (
                select(model)
                .where(model.task_id == task_id)
                .order_by(*order_cols)
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
        page_size = min(max(1, page_size), 200)
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
    async def get_available_tasks(platform: str, kind: str) -> list[dict]:
        """获取当前平台+类型数据中涉及的所有任务列表（带关键词和记录数）"""
        from database.system_models import CrawlerTask

        meta = PLATFORM_META.get(platform)
        if not meta:
            raise ValueError(f"不支持的平台: {platform}")
        kind_meta = meta["kinds"].get(kind)
        if not kind_meta:
            raise ValueError(f"不支持的数据类型: {kind}")

        model = kind_meta["model"]
        if not hasattr(model, "task_id"):
            return []

        async with get_mysql_session() as session:
            # 查询当前数据中的 DISTINCT task_id + 记录数，按 task_id 倒序（最新任务在前）
            stmt = (
                select(model.task_id, func.count(model.id).label("record_count"))
                .where(model.task_id.isnot(None))
                .group_by(model.task_id)
                .order_by(model.task_id.desc())
            )
            rows = (await session.execute(stmt)).all()

            if not rows:
                return []

            task_ids = [row[0] for row in rows if row[0]]
            count_map = {row[0]: row[1] for row in rows if row[0]}

            # 批量查询 crawler_task 获取关键词和状态
            task_stmt = select(CrawlerTask).where(CrawlerTask.id.in_(task_ids))
            task_rows = (await session.execute(task_stmt)).scalars().all()
            task_map = {t.id: t for t in task_rows}

            result = []
            for tid in task_ids:
                task = task_map.get(tid)
                payload = task.payload_snapshot if task else {}
                keywords = payload.get("keywords", "") if isinstance(payload, dict) else ""
                result.append({
                    "task_id": tid,
                    "keywords": keywords,
                    "status": task.status if task else "unknown",
                    "created_at": task.created_at.isoformat() if task and task.created_at else "",
                    "record_count": count_map.get(tid, 0),
                })

            return result

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
