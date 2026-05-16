# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.data_query_service import DataQueryService, list_platforms

router = APIRouter(prefix="/data/db", tags=["data-db"])


@router.get("/platforms")
async def get_db_platforms():
    return {"platforms": list_platforms()}


@router.get("/{platform}/{kind}")
async def query_data(
    platform: str,
    kind: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
):
    try:
        return await DataQueryService.query(platform, kind, page, page_size, keyword)
    except ValueError as e:
        raise HTTPException(400, str(e))
