# -*- coding: utf-8 -*-
"""平台系统表：配置方案与爬虫任务（与业务爬取表共用 Base）"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON

from database.models import Base


class CrawlerProfile(Base):
    """可复用的爬虫配置方案"""

    __tablename__ = "crawler_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True, comment="方案名称")
    description = Column(Text, default="", comment="说明")
    is_default = Column(Boolean, default=False, comment="是否默认方案")
    payload = Column(JSON, nullable=False, comment="完整配置 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrawlerTask(Base):
    """单次爬虫运行任务"""

    __tablename__ = "crawler_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, nullable=True, comment="来源方案 ID")
    status = Column(
        String(32),
        default="pending",
        comment="pending|running|completed|failed|cancelled",
    )
    payload_snapshot = Column(JSON, nullable=False, comment="启动时配置快照")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
