# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException

from config.db_config import mysql_db_config
from services.config_service import ConfigService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/database/status")
async def database_status():
    """检查 MySQL 连接（不建表）"""
    try:
        from sqlalchemy import text
        from database.db_session import get_mysql_session

        async with get_mysql_session() as session:
            await session.execute(text("SELECT 1"))
        return {
            "connected": True,
            "host": mysql_db_config["host"],
            "database": mysql_db_config["db_name"],
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.post("/init-database")
async def init_database():
    """创建数据库、业务表、系统表，并种子默认配置方案"""
    try:
        result = await ConfigService.init_database()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(500, f"初始化失败: {e}")
