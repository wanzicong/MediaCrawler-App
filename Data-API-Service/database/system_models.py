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


class KeywordGroup(Base):
    """关键词分组"""

    __tablename__ = "keyword_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True, comment="分组名称")
    description = Column(String(256), default="", comment="分组说明")
    color = Column(String(16), default="#6366f1", comment="分组颜色")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Keyword(Base):
    """关键词"""

    __tablename__ = "keyword"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, nullable=True, index=True, comment="所属分组 ID")
    keyword = Column(String(256), nullable=False, comment="关键词文本")
    platform = Column(String(32), default="xhs", comment="目标平台")
    source = Column(String(32), default="manual", comment="来源: manual / fission / ai")
    status = Column(String(32), default="pending", comment="状态: pending / crawled / has_results / no_results")
    crawled_count = Column(Integer, default=0, comment="已爬取条数")
    results_count = Column(Integer, default=0, comment="有效结果数")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrawlerAccount(Base):
    """平台账号（多账号管理）"""

    __tablename__ = "crawler_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False, index=True, comment="平台代码: xhs/dy/ks/bili/wb/tieba/zhihu")
    username = Column(String(128), default="", comment="用户名")
    phone = Column(String(32), default="", comment="手机号")
    cookies = Column(JSON, default=dict, comment="Cookie 字典")
    user_agent = Column(String(512), default="", comment="UA")
    status = Column(String(32), default="active", comment="active/cooling/banned/rate_limited")
    max_daily_requests = Column(Integer, default=500, comment="每日最大请求数")
    daily_request_count = Column(Integer, default=0, comment="今日已用请求数")
    total_request_count = Column(Integer, default=0, comment="累计请求数")
    cooldown_until = Column(DateTime, nullable=True, comment="冷却结束时间")
    last_used_at = Column(DateTime, nullable=True, comment="最后使用时间")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Platform(Base):
    """自媒体平台元数据（显示名称、图标、排序、启停）"""

    __tablename__ = "platform"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True, index=True, comment="平台代码: xhs/dy/ks/bili/wb/tieba/zhihu")
    name = Column(String(64), nullable=False, comment="平台显示名称")
    icon = Column(String(64), default="appstore", comment="前端图标名(Ant Design icon)")
    enabled = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序权重(越小越靠前)")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
