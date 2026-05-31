# -*- coding: utf-8 -*-
"""内容收藏 & 审阅状态 API"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from database.db_session import get_mysql_session
from database.system_models import ContentBookmark

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


class ToggleRequest(BaseModel):
    platform: str
    content_id: str


class StatusRequest(BaseModel):
    platform: str
    content_id: str
    review_status: Optional[str] = None


class BatchCheckRequest(BaseModel):
    platform: str
    content_ids: list[str]


@router.post("/toggle")
async def toggle_bookmark(req: ToggleRequest):
    """切换收藏状态：收藏 → 取消；未收藏 → 收藏"""
    async with get_mysql_session() as session:
        stmt = select(ContentBookmark).where(
            and_(
                ContentBookmark.platform == req.platform,
                ContentBookmark.content_id == req.content_id,
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.is_bookmarked = not existing.is_bookmarked
            existing.updated_at = datetime.utcnow()
            await session.commit()
            return {"is_bookmarked": existing.is_bookmarked, "action": "toggled"}
        else:
            bm = ContentBookmark(
                platform=req.platform,
                content_id=req.content_id,
                is_bookmarked=True,
            )
            session.add(bm)
            await session.commit()
            return {"is_bookmarked": True, "action": "created"}


@router.put("/status")
async def update_review_status(req: StatusRequest):
    """更新内容的审阅状态"""
    async with get_mysql_session() as session:
        stmt = select(ContentBookmark).where(
            and_(
                ContentBookmark.platform == req.platform,
                ContentBookmark.content_id == req.content_id,
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.review_status = req.review_status
            existing.updated_at = datetime.utcnow()
            await session.commit()
        else:
            bm = ContentBookmark(
                platform=req.platform,
                content_id=req.content_id,
                is_bookmarked=False,
                review_status=req.review_status,
            )
            session.add(bm)
            await session.commit()

        return {"ok": True, "review_status": req.review_status}


@router.get("/check")
async def check_bookmark(
    platform: str = Query(...),
    content_id: str = Query(...),
):
    """查询单个内容收藏 & 审阅状态"""
    async with get_mysql_session() as session:
        stmt = select(ContentBookmark).where(
            and_(
                ContentBookmark.platform == platform,
                ContentBookmark.content_id == content_id,
            )
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            return {
                "is_bookmarked": row.is_bookmarked,
                "review_status": row.review_status,
            }
        return {"is_bookmarked": False, "review_status": None}


@router.post("/batch-check")
async def batch_check_bookmarks(req: BatchCheckRequest):
    """批量查询内容收藏 & 审阅状态"""
    async with get_mysql_session() as session:
        stmt = select(ContentBookmark).where(
            and_(
                ContentBookmark.platform == req.platform,
                ContentBookmark.content_id.in_(req.content_ids),
            )
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        data = {}
        for row in rows:
            data[row.content_id] = {
                "is_bookmarked": row.is_bookmarked,
                "review_status": row.review_status,
            }
        # 未找到的默认为未收藏
        for cid in req.content_ids:
            if cid not in data:
                data[cid] = {"is_bookmarked": False, "review_status": None}
        return {"items": data}


@router.get("/list")
async def list_bookmarks(
    platform: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """分页列出某平台收藏的内容 ID 列表"""
    async with get_mysql_session() as session:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(ContentBookmark).where(
            and_(
                ContentBookmark.platform == platform,
                ContentBookmark.is_bookmarked == True,  # noqa: E712
            )
        )
        count_val = (await session.execute(count_stmt)).scalar() or 0

        list_stmt = (
            select(ContentBookmark)
            .where(
                and_(
                    ContentBookmark.platform == platform,
                    ContentBookmark.is_bookmarked == True,  # noqa: E712
                )
            )
            .order_by(ContentBookmark.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await session.execute(list_stmt)).scalars().all()

        return {
            "platform": platform,
            "items": [
                {
                    "content_id": r.content_id,
                    "review_status": r.review_status,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "updated_at": r.updated_at.isoformat() if r.updated_at else "",
                }
                for r in rows
            ],
            "total": count_val,
            "page": page,
            "page_size": page_size,
        }
