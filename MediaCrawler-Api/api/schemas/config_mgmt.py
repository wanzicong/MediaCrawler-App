# -*- coding: utf-8 -*-
from typing import Any, Optional

from pydantic import BaseModel, Field

from .crawler import CrawlerStartRequest


class CrawlerPayloadSchema(BaseModel):
    """与 MySQL payload 对齐的完整配置"""

    platform: str = "xhs"
    login_type: str = "qrcode"
    crawler_type: str = "search"
    keywords: str = ""
    specified_ids: str = ""
    creator_ids: str = ""
    start_page: int = 1
    enable_comments: bool = True
    enable_sub_comments: bool = False
    save_option: str = "db"
    cookies: str = ""
    headless: bool = False
    enable_cdp_mode: bool = True
    cdp_headless: bool = False
    enable_ip_proxy: bool = False
    ip_proxy_pool_count: int = 2
    ip_proxy_provider_name: str = "kuaidaili"
    crawler_max_notes_count: int = 100
    max_concurrency_num: int = 2
    crawler_max_comments_count_singlenotes: int = 30
    crawler_max_sleep_sec: int = 5
    crawler_max_sleep_sec_max: int = 15
    enable_get_medias: bool = False
    enable_get_wordcloud: bool = False
    save_login_state: bool = True
    xhs_international: bool = False


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    is_default: bool = False
    payload: CrawlerPayloadSchema


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    payload: Optional[CrawlerPayloadSchema] = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: str
    is_default: bool
    payload: dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CrawlerStartWithProfileRequest(CrawlerStartRequest):
    profile_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    profile_id: Optional[int]
    status: str
    payload_snapshot: dict[str, Any]
    error_message: Optional[str] = None
    progress: Optional[dict] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
