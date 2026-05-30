# -*- coding: utf-8 -*-
"""
Browser-Service - 浏览器管理独立服务

FastAPI 应用入口，端口 9500

提供:
- 浏览器实例池管理 (创建/销毁/列出/重启)
- 健康检查与自动恢复
- 运行时指标监控
- Cookie 持久化 (通过 user_data_dir)
"""

import logging
import os
import sys
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 确保项目根目录在 sys.path 中，支持相对导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers.browser import router as browser_router, inject_dependencies
from services.browser_pool import BrowserPool
from services.health_checker import HealthChecker

# ==================== 日志配置 ====================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("browser_service")

# ==================== 全局服务实例 ====================

pool: BrowserPool = BrowserPool()
health_checker: HealthChecker = HealthChecker(pool)
_startup_time = time.time()


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理

    启动时: 初始化浏览器池 + 启动后台健康检查
    关闭时: 停止健康检查 + 关闭所有浏览器实例
    """
    logger.info("=" * 60)
    logger.info("[Browser-Service] Starting up...")
    logger.info(f"[Browser-Service] System: {pool.system}")
    logger.info(f"[Browser-Service] Port range: {pool.find_available_port.__doc__}")
    logger.info("=" * 60)

    # 注入依赖到 browser router
    inject_dependencies(pool, health_checker)

    # 启动后台健康检查
    await health_checker.start()

    logger.info("[Browser-Service] Startup complete, ready to accept requests")

    yield  # 服务运行中...

    # ==================== 关闭流程 ====================
    logger.info("[Browser-Service] Shutting down...")

    # 停止后台任务
    await health_checker.stop()

    # 关闭所有浏览器实例
    await pool.shutdown_all()

    logger.info("[Browser-Service] Shutdown complete")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="Browser Service",
    description="浏览器管理独立服务 - Chrome/Edge 实例池管理、CDP 连接、健康检查与自动恢复",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由器
app.include_router(browser_router, prefix="/api/v1")


# ==================== 根路由 ====================

@app.get("/", include_in_schema=False)
async def root():
    """服务根路由"""
    return {
        "service": "Browser-Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "uptime_seconds": time.time() - _startup_time,
    }


# ==================== 直接启动 ====================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BROWSER_SERVICE_PORT", "9500"))
    host = os.getenv("BROWSER_SERVICE_HOST", "0.0.0.0")

    logger.info(f"Starting Browser-Service on {host}:{port}")
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=LOG_LEVEL.lower(),
    )
