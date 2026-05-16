# -*- coding: utf-8 -*-
"""从 MySQL 业务表分页查询爬取数据"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select

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
        "kinds": {
            "contents": {"model": XhsNote, "label": "笔记"},
            "comments": {"model": XhsNoteComment, "label": "评论"},
            "creators": {"model": XhsCreator, "label": "创作者"},
        },
    },
    "dy": {
        "label": "抖音",
        "kinds": {
            "contents": {"model": DouyinAweme, "label": "视频"},
            "comments": {"model": DouyinAwemeComment, "label": "评论"},
        },
    },
    "ks": {
        "label": "快手",
        "kinds": {
            "contents": {"model": KuaishouVideo, "label": "视频"},
            "comments": {"model": KuaishouVideoComment, "label": "评论"},
        },
    },
    "bili": {
        "label": "B站",
        "kinds": {
            "contents": {"model": BilibiliVideo, "label": "视频"},
            "comments": {"model": BilibiliVideoComment, "label": "评论"},
        },
    },
    "wb": {
        "label": "微博",
        "kinds": {
            "contents": {"model": WeiboNote, "label": "微博"},
            "comments": {"model": WeiboNoteComment, "label": "评论"},
        },
    },
    "tieba": {
        "label": "贴吧",
        "kinds": {
            "contents": {"model": TiebaNote, "label": "帖子"},
            "comments": {"model": TiebaComment, "label": "评论"},
        },
    },
    "zhihu": {
        "label": "知乎",
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
            "kinds": [
                {"value": k, "label": v["label"]} for k, v in meta["kinds"].items()
            ],
        }
        for key, meta in PLATFORM_META.items()
    ]


def _row_to_dict(row: Any) -> dict:
    data = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
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

            if keyword and hasattr(model, "title"):
                pattern = f"%{keyword}%"
                count_stmt = count_stmt.where(model.title.like(pattern))
                list_stmt = list_stmt.where(model.title.like(pattern))
            elif keyword and hasattr(model, "content_text"):
                pattern = f"%{keyword}%"
                count_stmt = count_stmt.where(model.content_text.like(pattern))
                list_stmt = list_stmt.where(model.content_text.like(pattern))

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
