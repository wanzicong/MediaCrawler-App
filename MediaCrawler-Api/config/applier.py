# -*- coding: utf-8 -*-
"""将 payload 字典应用到运行时 config 模块（兼容现有 crawler 代码）"""

from __future__ import annotations

from typing import Any

import config
from config.platform_risk_profiles import get_platform_profile


def apply_crawler_payload(payload: dict[str, Any]) -> None:
    """把配置快照写入全局 config，供爬虫与 store 使用"""
    platform = payload.get("platform", config.PLATFORM)
    config.PLATFORM = platform
    config.LOGIN_TYPE = payload.get("login_type", config.LOGIN_TYPE)
    config.CRAWLER_TYPE = payload.get("crawler_type", config.CRAWLER_TYPE)
    config.KEYWORDS = payload.get("keywords", config.KEYWORDS)
    config.START_PAGE = int(payload.get("start_page", config.START_PAGE))
    config.ENABLE_GET_COMMENTS = bool(payload.get("enable_comments", config.ENABLE_GET_COMMENTS))
    config.ENABLE_GET_SUB_COMMENTS = bool(
        payload.get("enable_sub_comments", config.ENABLE_GET_SUB_COMMENTS)
    )
    config.SAVE_DATA_OPTION = "db"
    config.COOKIES = payload.get("cookies", config.COOKIES)
    config.HEADLESS = bool(payload.get("headless", config.HEADLESS))
    config.CDP_HEADLESS = config.HEADLESS

    config.ENABLE_CDP_MODE = bool(payload.get("enable_cdp_mode", config.ENABLE_CDP_MODE))
    config.ENABLE_IP_PROXY = bool(payload.get("enable_ip_proxy", config.ENABLE_IP_PROXY))
    config.IP_PROXY_POOL_COUNT = int(
        payload.get("ip_proxy_pool_count", config.IP_PROXY_POOL_COUNT)
    )
    config.IP_PROXY_PROVIDER_NAME = payload.get(
        "ip_proxy_provider_name", config.IP_PROXY_PROVIDER_NAME
    )
    config.CRAWLER_MAX_NOTES_COUNT = int(
        payload.get("crawler_max_notes_count", config.CRAWLER_MAX_NOTES_COUNT)
    )
    config.MAX_CONCURRENCY_NUM = int(payload.get("max_concurrency_num", config.MAX_CONCURRENCY_NUM))
    config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = int(
        payload.get(
            "crawler_max_comments_count_singlenotes",
            config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
        )
    )
    config.CRAWLER_MAX_SLEEP_SEC = int(
        payload.get("crawler_max_sleep_sec", config.CRAWLER_MAX_SLEEP_SEC)
    )
    if hasattr(config, "CRAWLER_MAX_SLEEP_SEC_MAX"):
        config.CRAWLER_MAX_SLEEP_SEC_MAX = int(
            payload.get("crawler_max_sleep_sec_max", config.CRAWLER_MAX_SLEEP_SEC_MAX)
        )
    config.ENABLE_GET_MEIDAS = bool(payload.get("enable_get_medias", config.ENABLE_GET_MEIDAS))
    config.ENABLE_GET_WORDCLOUD = bool(
        payload.get("enable_get_wordcloud", config.ENABLE_GET_WORDCLOUD)
    )
    config.SAVE_LOGIN_STATE = bool(payload.get("save_login_state", config.SAVE_LOGIN_STATE))
    if hasattr(config, "XHS_INTERNATIONAL"):
        config.XHS_INTERNATIONAL = bool(
            payload.get("xhs_international", config.XHS_INTERNATIONAL)
        )

    _apply_platform_ids(platform, payload)
    _apply_platform_risk_profile(platform)


def _apply_platform_ids(platform: str, payload: dict[str, Any]) -> None:
    specified = payload.get("specified_ids") or ""
    creator = payload.get("creator_ids") or ""
    specified_list = [x.strip() for x in specified.split(",") if x.strip()]
    creator_list = [x.strip() for x in creator.split(",") if x.strip()]

    if not specified_list and not creator_list:
        return

    if specified_list:
        if platform == "xhs":
            config.XHS_SPECIFIED_NOTE_URL_LIST = specified_list
        elif platform == "bili":
            config.BILI_SPECIFIED_ID_LIST = specified_list
        elif platform == "dy":
            config.DY_SPECIFIED_ID_LIST = specified_list
        elif platform == "wb":
            config.WEIBO_SPECIFIED_ID_LIST = specified_list
        elif platform == "ks":
            config.KS_SPECIFIED_ID_LIST = specified_list
        elif platform == "tieba":
            import re

            config.TIEBA_SPECIFIED_ID_LIST = [
                re.search(r"/p/(\d+)", item).group(1)
                if re.search(r"/p/(\d+)", item)
                else item
                for item in specified_list
            ]

    if creator_list:
        if platform == "xhs":
            config.XHS_CREATOR_ID_LIST = creator_list
        elif platform == "bili":
            config.BILI_CREATOR_ID_LIST = creator_list
        elif platform == "dy":
            config.DY_CREATOR_ID_LIST = creator_list
        elif platform == "wb":
            config.WEIBO_CREATOR_ID_LIST = creator_list
        elif platform == "ks":
            config.KS_CREATOR_ID_LIST = creator_list
        elif platform == "tieba":
            config.TIEBA_CREATOR_URL_LIST = [
                item
                if item.startswith("http")
                else f"https://tieba.baidu.com/home/main?id={item}"
                for item in creator_list
            ]


def _apply_platform_risk_profile(platform: str) -> None:
    """根据平台风险配置，对运行时 config 施加安全边界"""
    profile = get_platform_profile(platform)
    risk_level = profile["risk_level"]

    sleep_min, sleep_max = profile["sleep_interval"]
    if config.CRAWLER_MAX_SLEEP_SEC < sleep_min:
        print(f"[RiskProfile] {platform} 最小间隔从 {config.CRAWLER_MAX_SLEEP_SEC}s 调整为 {sleep_min}s（风控等级 {risk_level}）")
        config.CRAWLER_MAX_SLEEP_SEC = sleep_min
    if hasattr(config, "CRAWLER_MAX_SLEEP_SEC_MAX") and config.CRAWLER_MAX_SLEEP_SEC_MAX < sleep_max:
        print(f"[RiskProfile] {platform} 最大间隔从 {config.CRAWLER_MAX_SLEEP_SEC_MAX}s 调整为 {sleep_max}s（风控等级 {risk_level}）")
        config.CRAWLER_MAX_SLEEP_SEC_MAX = sleep_max

    if config.MAX_CONCURRENCY_NUM > profile["max_concurrency"]:
        print(f"[RiskProfile] {platform} 并发数从 {config.MAX_CONCURRENCY_NUM} 调整为 {profile['max_concurrency']}（风控等级 {risk_level}）")
        config.MAX_CONCURRENCY_NUM = profile["max_concurrency"]

    if config.CRAWLER_MAX_NOTES_COUNT > profile["max_notes"]:
        print(f"[RiskProfile] {platform} 最大条数从 {config.CRAWLER_MAX_NOTES_COUNT} 调整为 {profile['max_notes']}（风控等级 {risk_level}）")
        config.CRAWLER_MAX_NOTES_COUNT = profile["max_notes"]

    if profile.get("require_cdp") and not config.ENABLE_CDP_MODE:
        print(f"[RiskProfile] {platform} 强制开启 CDP 模式（风控等级 {risk_level}）")
        config.ENABLE_CDP_MODE = True
