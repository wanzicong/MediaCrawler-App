# -*- coding: utf-8 -*-
# Redis/Cache 配置 — 供 cache 和 proxy 模块使用
import os

REDIS_DB_HOST = os.getenv("REDIS_DB_HOST", "127.0.0.1")
REDIS_DB_PORT = int(os.getenv("REDIS_DB_PORT", "6379"))
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "")
REDIS_DB_NUM = int(os.getenv("REDIS_DB_NUM", "0"))

CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "local"
CACHE_TYPE_REDIS_ENABLED = os.getenv("CACHE_TYPE_REDIS_ENABLED", "0") == "1"
