# -*- coding: utf-8 -*-
"""平台差异化风控配置 — 每个平台独立的间隔/并发/限量参数"""

PLATFORM_RISK_PROFILES = {
    "xhs": {
        "risk_level": 5,
        "sleep_interval": (8, 20),
        "max_concurrency": 1,
        "max_notes": 100,
        "ua_type": "mobile",
        "require_cdp": True,
        "cookie_ttl_hours": 2,
    },
    "dy": {
        "risk_level": 4,
        "sleep_interval": (5, 15),
        "max_concurrency": 1,
        "max_notes": 80,
        "ua_type": "mobile",
        "require_cdp": True,
    },
    "bili": {
        "risk_level": 3,
        "sleep_interval": (3, 10),
        "max_concurrency": 3,
        "max_notes": 300,
        "ua_type": "desktop",
        "require_cdp": False,
    },
    "wb": {
        "risk_level": 3,
        "sleep_interval": (3, 10),
        "max_concurrency": 2,
        "max_notes": 150,
        "ua_type": "desktop",
        "require_cdp": False,
    },
    "ks": {
        "risk_level": 3,
        "sleep_interval": (4, 12),
        "max_concurrency": 2,
        "max_notes": 100,
        "ua_type": "mobile",
        "require_cdp": True,
    },
    "tieba": {
        "risk_level": 2,
        "sleep_interval": (2, 6),
        "max_concurrency": 5,
        "max_notes": 500,
        "ua_type": "desktop",
        "require_cdp": False,
    },
    "zhihu": {
        "risk_level": 2,
        "sleep_interval": (2, 8),
        "max_concurrency": 4,
        "max_notes": 200,
        "ua_type": "desktop",
        "require_cdp": False,
    },
}


def get_platform_profile(platform: str) -> dict:
    """获取指定平台的风控配置，未匹配时返回温和默认值"""
    return PLATFORM_RISK_PROFILES.get(
        platform,
        {
            "risk_level": 3,
            "sleep_interval": (3, 10),
            "max_concurrency": 2,
            "max_notes": 150,
            "ua_type": "desktop",
        },
    )
