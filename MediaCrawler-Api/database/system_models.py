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
    progress = Column(JSON, nullable=True, comment="爬取进度快照 {page, keyword, crawled_count}")
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class ChatSession(Base):
    """AI 对话会话"""

    __tablename__ = "chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False, default="新对话", comment="会话标题")
    messages = Column(JSON, nullable=False, default=list, comment="消息列表 [{role, content, timestamp}]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMemory(Base):
    """AI 记忆条目"""

    __tablename__ = "chat_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), nullable=False, unique=True, comment="记忆标识")
    content = Column(Text, nullable=False, comment="记忆内容")
    category = Column(String(64), default="通用", comment="分类标签")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
