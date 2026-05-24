# -*- coding: utf-8 -*-
"""平台管理 API：列出、更新、排序"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.platform_service import PlatformService

router = APIRouter(prefix="/platforms", tags=["platforms"])


class PlatformUpdateRequest(BaseModel):
    name: str | None = Field(None, description="平台显示名称")
    icon: str | None = Field(None, description="Ant Design 图标名")
    enabled: bool | None = Field(None, description="是否启用")
    sort_order: int | None = Field(None, description="排序权重")


class ReorderRequest(BaseModel):
    order: list[int] = Field(..., min_length=1, description="按期望顺序排列的 ID 列表")


@router.get("")
async def list_platforms(enabled_only: bool = False):
    """获取平台列表，支持 ?enabled_only=true 过滤已禁用的平台"""
    return await PlatformService.list_platforms(enabled_only=enabled_only)


@router.put("/reorder")
async def reorder_platforms(body: ReorderRequest):
    """批量调整平台排序"""
    await PlatformService.reorder_platforms(body.order)
    # 刷新 data_query_service 的 PLATFORM_META 缓存
    from services.data_query_service import init_platform_meta
    await init_platform_meta()
    return {"status": "ok"}


@router.put("/{platform_id}")
async def update_platform(platform_id: int, body: PlatformUpdateRequest):
    """更新平台元数据"""
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "请至少提供一个需要更新的字段")
    result = await PlatformService.update_platform(platform_id, data)
    if result is None:
        raise HTTPException(404, f"平台 {platform_id} 不存在")
    # 刷新 data_query_service 的 PLATFORM_META 缓存
    from services.data_query_service import init_platform_meta
    await init_platform_meta()
    return result
