# -*- coding: utf-8 -*-
"""平台元数据服务：将平台显示信息从硬编码迁移到数据库"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update

from database.db_session import get_mysql_session
from database.system_models import Platform
from database.models import (
    XhsNote,
    XhsNoteComment,
    XhsCreator,
    DouyinAweme,
    DouyinAwemeComment,
    KuaishouVideo,
    KuaishouVideoComment,
    BilibiliVideo,
    BilibiliVideoComment,
    WeiboNote,
    WeiboNoteComment,
    TiebaNote,
    TiebaComment,
    ZhihuContent,
    ZhihuComment,
)

# ── 平台代码 → 数据模型/字段映射（代码层面，不可入库） ──────────────────
_PLATFORM_MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "xhs": {
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": XhsNote, "label": "笔记"},
            "comments": {"model": XhsNoteComment, "label": "评论"},
            "creators": {"model": XhsCreator, "label": "创作者"},
        },
    },
    "dy": {
        "content_id_field": "aweme_id",
        "kinds": {
            "contents": {"model": DouyinAweme, "label": "视频"},
            "comments": {"model": DouyinAwemeComment, "label": "评论"},
        },
    },
    "ks": {
        "content_id_field": "video_id",
        "kinds": {
            "contents": {"model": KuaishouVideo, "label": "视频"},
            "comments": {"model": KuaishouVideoComment, "label": "评论"},
        },
    },
    "bili": {
        "content_id_field": "video_id",
        "kinds": {
            "contents": {"model": BilibiliVideo, "label": "视频"},
            "comments": {"model": BilibiliVideoComment, "label": "评论"},
        },
    },
    "wb": {
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": WeiboNote, "label": "微博"},
            "comments": {"model": WeiboNoteComment, "label": "评论"},
        },
    },
    "tieba": {
        "content_id_field": "note_id",
        "kinds": {
            "contents": {"model": TiebaNote, "label": "帖子"},
            "comments": {"model": TiebaComment, "label": "评论"},
        },
    },
    "zhihu": {
        "content_id_field": "content_id",
        "kinds": {
            "contents": {"model": ZhihuContent, "label": "内容"},
            "comments": {"model": ZhihuComment, "label": "评论"},
        },
    },
}

# 默认种子数据
_DEFAULT_PLATFORMS = [
    {"code": "xhs", "name": "小红书", "icon": "book-open", "sort_order": 1},
    {"code": "dy", "name": "抖音", "icon": "music", "sort_order": 2},
    {"code": "ks", "name": "快手", "icon": "video", "sort_order": 3},
    {"code": "bili", "name": "B站", "icon": "tv", "sort_order": 4},
    {"code": "wb", "name": "微博", "icon": "message-circle", "sort_order": 5},
    {"code": "tieba", "name": "贴吧", "icon": "messages-square", "sort_order": 6},
    {"code": "zhihu", "name": "知乎", "icon": "help-circle", "sort_order": 7},
]


def _row_to_dict(row: Platform) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "icon": row.icon,
        "enabled": row.enabled,
        "sort_order": row.sort_order,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class PlatformService:
    """平台元数据 CRUD 服务"""

    @staticmethod
    async def list_platforms(enabled_only: bool = False) -> list[dict]:
        """列出所有平台（按 sort_order 排序）"""
        async with get_mysql_session() as session:
            stmt = select(Platform).order_by(Platform.sort_order)
            if enabled_only:
                stmt = stmt.where(Platform.enabled == True)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def get_platform_meta() -> dict[str, dict]:
        """
        获取平台元数据字典（与旧 PLATFORM_META 结构一致）。

        仅返回 已启用 且 模型配置存在 的平台。
        返回格式示例:
        {
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
          ...
        }
        """
        platforms = await PlatformService.list_platforms(enabled_only=True)
        result: dict[str, dict] = {}
        for p in platforms:
            code = p["code"]
            if code not in _PLATFORM_MODEL_CONFIG:
                continue
            model_cfg = _PLATFORM_MODEL_CONFIG[code]
            result[code] = {
                "label": p["name"],
                "icon": p["icon"],
                "sort_order": p["sort_order"],
                "content_id_field": model_cfg["content_id_field"],
                "kinds": model_cfg["kinds"],
            }
        return result

    @staticmethod
    async def update_platform(platform_id: int, data: dict) -> dict | None:
        """更新平台字段（name, icon, enabled, sort_order）"""
        allowed_keys = {"name", "icon", "enabled", "sort_order"}
        updates = {k: v for k, v in data.items() if k in allowed_keys}
        if not updates:
            return None

        async with get_mysql_session() as session:
            stmt = (
                update(Platform)
                .where(Platform.id == platform_id)
                .values(**updates)
            )
            await session.execute(stmt)
            await session.commit()

            # 回读更新后的数据
            result = await session.execute(select(Platform).where(Platform.id == platform_id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return _row_to_dict(row)

    @staticmethod
    async def reorder_platforms(order: list[int]) -> None:
        """根据 ID 列表批量更新 sort_order"""
        async with get_mysql_session() as session:
            for idx, pid in enumerate(order):
                stmt = (
                    update(Platform)
                    .where(Platform.id == pid)
                    .values(sort_order=idx + 1)
                )
                await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def seed_default_platforms():
        """如果 platform 表为空则插入默认的 7 个平台"""
        async with get_mysql_session() as session:
            result = await session.execute(select(Platform.id).limit(1))
            if result.scalar_one_or_none() is not None:
                return  # 已有数据，跳过种子

            for item in _DEFAULT_PLATFORMS:
                platform = Platform(
                    code=item["code"],
                    name=item["name"],
                    icon=item["icon"],
                    enabled=True,
                    sort_order=item["sort_order"],
                )
                session.add(platform)
            await session.commit()
