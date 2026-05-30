# -*- coding: utf-8 -*-
"""
Pydantic 请求/响应模型
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class CreateInstanceRequest(BaseModel):
    """创建浏览器实例请求"""
    headless: bool = Field(default=False, description="是否无头模式")
    platform: str = Field(default="", description="平台标识 (xhs/dy/ks/bili/wb/tieba/zhihu)")
    user_data_dir: Optional[str] = Field(default=None, description="用户数据目录路径 (Cookie 持久化)")


class DeleteInstanceRequest(BaseModel):
    """删除浏览器实例请求"""
    force: bool = Field(default=False, description="是否强制 kill")


# ==================== 响应模型 ====================

class BrowserInstanceResponse(BaseModel):
    """浏览器实例响应"""
    instance_id: str
    debug_port: int
    pid: Optional[int] = None
    browser_name: str = ""
    headless: bool = False
    platform_name: str = ""
    status: str = "starting"
    ws_url: str = ""
    created_at: float = 0
    uptime: float = 0
    context_count: int = 0
    health_fail_count: int = 0

    class Config:
        from_attributes = True


class CreateInstanceResponse(BaseModel):
    """创建实例响应"""
    instance_id: str
    debug_port: int
    ws_url: str
    status: str
    browser_name: str = ""
    platform_name: str = ""


class HealthCheckResponse(BaseModel):
    """单实例健康检查响应"""
    status: str = "unknown"           # ok / unhealthy / starting / stopped / not_found
    instance_id: str = ""
    debug_port: Optional[int] = None
    pid: Optional[int] = None
    uptime: float = 0
    detail: Optional[str] = None


class ServiceHealthResponse(BaseModel):
    """服务整体健康响应"""
    status: str = "ok"
    version: str = "1.0.0"
    instances_ready: int = 0
    instances_total: int = 0


class MetricsResponse(BaseModel):
    """运行时指标响应"""
    total_instances: int = 0
    ready: int = 0
    unhealthy: int = 0
    starting: int = 0
    stopped: int = 0
    port_range: str = "9222-9321"
    pool_size: int = 5
    system: str = ""
    health_checker_uptime: float = 0
    service_uptime: float = 0


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    detail: Optional[str] = None
