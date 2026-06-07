# -*- coding: utf-8 -*-
"""共享的内部 API 请求头（自动注入 X-API-Token）"""
import os

_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-dev-token")
INTERNAL_HEADERS = {"X-API-Token": _TOKEN}
