# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/main.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
Data API Service
Start command: uvicorn api.main:app --port 8080 --reload
"""
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    ai_router,
    config_mgmt_router,
    data_db_router,
    data_router,
    internal_router,
    keywords_router,
    platforms_router,
    system_router,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from services.config_service import ConfigService

        await ConfigService.ensure_default_profile()
    except Exception:
        pass

    # 平台元数据：种子默认数据 + 初始化缓存
    try:
        from services.platform_service import PlatformService
        from services.data_query_service import init_platform_meta

        await PlatformService.seed_default_platforms()
        await init_platform_meta()
    except Exception:
        pass

    yield


app = FastAPI(
    title="MediaCrawler Data API Service",
    description="Data/AI/Config API for MediaCrawler",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration - allow frontend dev server access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:10001",  # Vite dev server
        "http://localhost:3000",  # Backup port
        "http://127.0.0.1:10001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ai_router, prefix="/api")
app.include_router(config_mgmt_router, prefix="/api")
app.include_router(data_db_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(internal_router)
app.include_router(keywords_router, prefix="/api")
app.include_router(platforms_router, prefix="/api")
app.include_router(system_router, prefix="/api")


@app.get("/")
async def root():
    """Service root"""
    return {
        "service": "MediaCrawler Data API Service",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/env/check")
async def env_check():
    """检查运行环境和基础服务连通性"""
    import os
    from pathlib import Path
    import platform as sys_platform
    import sys

    checks = {}

    # Python 版本
    checks["python_version"] = sys.version

    # .env 文件是否存在
    env_path = Path(__file__).resolve().parent.parent / ".env"
    checks["env_file_exists"] = env_path.exists()

    # MySQL 连通性
    try:
        from sqlalchemy import text
        from database.db_session import get_mysql_session

        async with get_mysql_session() as session:
            await session.execute(text("SELECT 1"))
        checks["mysql"] = True
    except Exception as e:
        checks["mysql"] = str(e)

    # Redis 连通性
    try:
        import redis
        from config.db_config import REDIS_DB_HOST, REDIS_DB_PORT, REDIS_DB_PWD, REDIS_DB_NUM

        r = redis.Redis(
            host=REDIS_DB_HOST,
            port=int(REDIS_DB_PORT),
            password=REDIS_DB_PWD or None,
            db=int(REDIS_DB_NUM),
            socket_connect_timeout=3,
        )
        r.ping()
        r.close()
        checks["redis"] = True
    except Exception as e:
        checks["redis"] = str(e)

    # 操作系统
    checks["os"] = sys_platform.system()
    checks["hostname"] = sys_platform.node()

    # Crawler-Service 连通性
    crawler_url = os.getenv("DATA_API_URL", "http://127.0.0.1:8080").replace(":8080", ":8081")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{crawler_url}/api/crawler/status")
        checks["crawler_service"] = "ok" if resp.status_code == 200 else f"status {resp.status_code}"
    except Exception as e:
        checks["crawler_service"] = str(e)

    all_ok = isinstance(checks.get("mysql"), bool) and checks.get("mysql")
    return {
        "success": all_ok,
        "message": "所有基础服务连接正常" if all_ok else "部分服务不可用",
        "checks": checks,
        "error": None if all_ok else "部分服务不可用，详见 checks",
    }


@app.get("/api/config/platforms")
async def get_platforms():
    """Get list of supported platforms"""
    from services.data_query_service import list_platforms
    return {"platforms": list_platforms()}


@app.get("/api/config/options")
async def get_config_options():
    """Get all configuration options"""
    return {
        "login_types": [
            {"value": "qrcode", "label": "扫码登录"},
            {"value": "cookie", "label": "Cookie登录"},
        ],
        "crawler_types": [
            {"value": "search", "label": "搜索模式"},
            {"value": "detail", "label": "详情模式"},
            {"value": "creator", "label": "创作者模式"},
        ],
        "save_options": [
            {"value": "db", "label": "MySQL数据库（默认）"},
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
