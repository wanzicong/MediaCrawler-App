# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException

from ..schemas.config_mgmt import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/schema")
async def get_config_schema():
    """前端动态表单字段元数据"""
    return {
        "groups": [
            {
                "key": "basic",
                "label": "基础配置",
                "fields": [
                    {"key": "platform", "label": "平台", "type": "platform"},
                    {"key": "login_type", "label": "登录方式", "type": "select"},
                    {"key": "crawler_type", "label": "爬取模式", "type": "select"},
                    {"key": "keywords", "label": "关键词", "type": "text", "when": {"crawler_type": "search"}},
                    {"key": "specified_ids", "label": "帖子/视频 ID", "type": "textarea", "when": {"crawler_type": "detail"}},
                    {"key": "creator_ids", "label": "创作者 ID", "type": "textarea", "when": {"crawler_type": "creator"}},
                    {"key": "start_page", "label": "起始页", "type": "number"},
                    {"key": "cookies", "label": "Cookie", "type": "textarea"},
                    {"key": "headless", "label": "无头模式", "type": "switch"},
                ],
            },
            {
                "key": "comment",
                "label": "评论",
                "fields": [
                    {"key": "enable_comments", "label": "抓取评论", "type": "switch"},
                    {"key": "enable_sub_comments", "label": "子评论", "type": "switch"},
                    {"key": "crawler_max_comments_count_singlenotes", "label": "单条最大评论数", "type": "number"},
                ],
            },
            {
                "key": "advanced",
                "label": "高级",
                "fields": [
                    {"key": "enable_cdp_mode", "label": "CDP 模式", "type": "switch"},
                    {"key": "enable_ip_proxy", "label": "IP 代理", "type": "switch"},
                    {"key": "ip_proxy_pool_count", "label": "代理池数量", "type": "number"},
                    {"key": "crawler_max_notes_count", "label": "最大爬取条数", "type": "number"},
                    {"key": "crawler_max_sleep_sec", "label": "爬取间隔(秒)", "type": "number"},
                    {"key": "enable_get_medias", "label": "下载媒体", "type": "switch"},
                    {"key": "save_login_state", "label": "保存登录态", "type": "switch"},
                ],
            },
        ],
        "storage_note": "数据存储固定为 MySQL（save_option=db）",
    }


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles():
    return await ConfigService.list_profiles()


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: int):
    data = await ConfigService.get_profile(profile_id)
    if not data:
        raise HTTPException(404, "方案不存在")
    return data


@router.post("/profiles", response_model=ProfileResponse)
async def create_profile(body: ProfileCreateRequest):
    return await ConfigService.create_profile(
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        payload=body.payload.model_dump(),
    )


@router.put("/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: int, body: ProfileUpdateRequest):
    data = await ConfigService.update_profile(
        profile_id,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        payload=body.payload.model_dump() if body.payload else None,
    )
    if not data:
        raise HTTPException(404, "方案不存在")
    return data


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: int):
    try:
        ok = await ConfigService.delete_profile(profile_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "方案不存在")
    return {"status": "ok"}


@router.post("/profiles/{profile_id}/default", response_model=ProfileResponse)
async def set_default_profile(profile_id: int):
    data = await ConfigService.set_default_profile(profile_id)
    if not data:
        raise HTTPException(404, "方案不存在")
    return data
