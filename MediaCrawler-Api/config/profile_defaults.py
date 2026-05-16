# -*- coding: utf-8 -*-
"""从当前 config 模块生成默认 payload 字典（用于种子数据与 API）"""

from __future__ import annotations

from typing import Any

import config


def build_default_payload() -> dict[str, Any]:
    """构建与 Web/API 对齐的默认配置快照"""
    return {
        "platform": config.PLATFORM,
        "login_type": config.LOGIN_TYPE,
        "crawler_type": config.CRAWLER_TYPE,
        "keywords": config.KEYWORDS,
        "specified_ids": "",
        "creator_ids": "",
        "start_page": config.START_PAGE,
        "enable_comments": config.ENABLE_GET_COMMENTS,
        "enable_sub_comments": config.ENABLE_GET_SUB_COMMENTS,
        "save_option": "db",
        "cookies": config.COOKIES,
        "headless": config.HEADLESS,
        "enable_cdp_mode": config.ENABLE_CDP_MODE,
        "cdp_headless": config.CDP_HEADLESS,
        "enable_ip_proxy": config.ENABLE_IP_PROXY,
        "ip_proxy_pool_count": config.IP_PROXY_POOL_COUNT,
        "ip_proxy_provider_name": config.IP_PROXY_PROVIDER_NAME,
        "crawler_max_notes_count": config.CRAWLER_MAX_NOTES_COUNT,
        "max_concurrency_num": config.MAX_CONCURRENCY_NUM,
        "crawler_max_comments_count_singlenotes": config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
        "crawler_max_sleep_sec": config.CRAWLER_MAX_SLEEP_SEC,
        "enable_get_medias": config.ENABLE_GET_MEIDAS,
        "enable_get_wordcloud": config.ENABLE_GET_WORDCLOUD,
        "save_login_state": config.SAVE_LOGIN_STATE,
        "xhs_international": getattr(config, "XHS_INTERNATIONAL", False),
    }
