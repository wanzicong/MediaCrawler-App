# -*- coding: utf-8 -*-
"""将已有 MySQL 表结构补齐到与 ORM 一致（幂等，可重复执行）"""

from __future__ import annotations

from sqlalchemy import text

from database.db_session import get_mysql_session

# (table, column, ddl_fragment) — ddl_fragment 不含 ADD COLUMN 前缀
_SCHEMA_PATCHES: list[tuple[str, str, str]] = [
    ("crawler_task", "progress", "JSON NULL COMMENT '爬取进度快照'"),
]

_BUSINESS_TABLES = [
    "bilibili_video",
    "bilibili_video_comment",
    "bilibili_up_info",
    "bilibili_contact_info",
    "bilibili_up_dynamic",
    "douyin_aweme",
    "douyin_aweme_comment",
    "dy_creator",
    "kuaishou_video",
    "kuaishou_video_comment",
    "weibo_note",
    "weibo_note_comment",
    "weibo_creator",
    "xhs_note",
    "xhs_note_comment",
    "xhs_creator",
    "tieba_note",
    "tieba_comment",
    "tieba_creator",
    "zhihu_content",
    "zhihu_comment",
    "zhihu_creator",
]

for _table in _BUSINESS_TABLES:
    _SCHEMA_PATCHES.append(
        (_table, "task_id", "BIGINT NULL COMMENT '关联爬取任务ID'")
    )


async def _column_exists(session, table: str, column: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column"
        ),
        {"table": table, "column": column},
    )
    return bool(result.scalar())


async def sync_schema() -> list[str]:
    """补齐缺失列，返回已应用的变更描述列表"""
    applied: list[str] = []
    async with get_mysql_session() as session:
        for table, column, ddl in _SCHEMA_PATCHES:
            if await _column_exists(session, table, column):
                continue
            await session.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl}"))
            applied.append(f"{table}.{column}")
    return applied
