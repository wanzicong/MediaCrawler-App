# -*- coding: utf-8 -*-
"""
浏览器管理 API Router

端点:
  POST   /api/v1/instances              - 创建浏览器实例
  GET    /api/v1/instances              - 列出所有实例
  DELETE /api/v1/instances/{id}         - 销毁实例
  GET    /api/v1/instances/{id}         - 获取实例详情
  GET    /api/v1/instances/{id}/health  - 单实例健康检查
  POST   /api/v1/instances/{id}/restart - 重启实例
  GET    /api/v1/health                 - 服务整体健康检查
  GET    /api/v1/metrics                - 运行时指标
"""

import logging
import time

from fastapi import APIRouter, HTTPException, Query, Request

from api.schemas import (
    CreateInstanceRequest,
    CreateInstanceResponse,
    BrowserInstanceResponse,
    HealthCheckResponse,
    ServiceHealthResponse,
    MetricsResponse,
    MessageResponse,
)
from services.browser_pool import BrowserPool, POOL_SIZE
from services.health_checker import HealthChecker

logger = logging.getLogger("browser_api")

router = APIRouter()

# 全局服务引用（在 main.py 中注入）
pool: BrowserPool = None  # type: ignore[assignment]
health_checker: HealthChecker = None  # type: ignore[assignment]
service_start_time = time.time()


def inject_dependencies(browser_pool: BrowserPool, hc: HealthChecker):
    """注入依赖（由 main.py 在 startup 中调用）"""
    global pool, health_checker
    pool = browser_pool
    health_checker = hc


# ==================== 实例管理 ====================


@router.post(
    "/instances",
    response_model=CreateInstanceResponse,
    summary="创建浏览器实例",
    description="启动一个新的 Chrome/Edge 浏览器实例并返回 CDP 连接信息",
)
async def create_instance(req: CreateInstanceRequest) -> CreateInstanceResponse:
    """
    创建浏览器实例

    - **headless**: 是否无头模式 (默认 false)
    - **platform**: 平台标识，用于区分 user_data_dir (xhs/dy/ks/bili/wb/tieba/zhihu)
    - **user_data_dir**: 自定义用户数据目录路径，用于 Cookie 持久化
    """
    try:
        instance = await pool.create_instance(
            headless=req.headless,
            platform=req.platform,
            user_data_dir=req.user_data_dir,
        )

        return CreateInstanceResponse(
            instance_id=instance.instance_id,
            debug_port=instance.debug_port,
            ws_url=instance.ws_url,
            status=instance.status,
            browser_name=instance.browser_name,
            platform_name=instance.platform_name,
        )
    except RuntimeError as e:
        logger.error(f"[API] Failed to create instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Unexpected error creating instance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/instances",
    response_model=list[BrowserInstanceResponse],
    summary="列出所有浏览器实例",
    description="返回所有浏览器实例的列表，可按状态过滤",
)
async def list_instances(
    status: str = Query(default=None, description="按状态过滤: ready/unhealthy/starting/stopped"),
) -> list[BrowserInstanceResponse]:
    """
    列出所有浏览器实例，可选按状态过滤
    """
    instances = await pool.list_instances(status_filter=status)

    response_list = []
    for inst in instances:
        uptime = time.time() - inst.created_at if inst.created_at else 0
        response_list.append(
            BrowserInstanceResponse(
                instance_id=inst.instance_id,
                debug_port=inst.debug_port,
                pid=inst.pid,
                browser_name=inst.browser_name,
                headless=inst.headless,
                platform_name=inst.platform_name,
                status=inst.status,
                ws_url=inst.ws_url,
                created_at=inst.created_at,
                uptime=uptime,
                context_count=inst.context_count,
                health_fail_count=inst.health_fail_count,
            )
        )

    return response_list


@router.get(
    "/instances/{instance_id}",
    response_model=BrowserInstanceResponse,
    summary="获取实例详情",
    description="获取指定浏览器实例的详细信息",
)
async def get_instance(instance_id: str) -> BrowserInstanceResponse:
    """
    获取指定实例的详细信息
    """
    instance = await pool.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    uptime = time.time() - instance.created_at if instance.created_at else 0
    return BrowserInstanceResponse(
        instance_id=instance.instance_id,
        debug_port=instance.debug_port,
        pid=instance.pid,
        browser_name=instance.browser_name,
        headless=instance.headless,
        platform_name=instance.platform_name,
        status=instance.status,
        ws_url=instance.ws_url,
        created_at=instance.created_at,
        uptime=uptime,
        context_count=instance.context_count,
        health_fail_count=instance.health_fail_count,
    )


@router.delete(
    "/instances/{instance_id}",
    response_model=MessageResponse,
    summary="销毁浏览器实例",
    description="关闭浏览器进程并释放端口",
)
async def delete_instance(
    instance_id: str,
    force: bool = Query(default=False, description="是否强制 kill"),
) -> MessageResponse:
    """
    销毁指定浏览器实例

    - **force**: 设置为 true 跳过优雅关闭，直接 SIGKILL
    """
    try:
        success = await pool.destroy_instance(instance_id, force=force)
        if not success:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        return MessageResponse(
            message="Instance destroyed successfully",
            detail=f"instance_id={instance_id}, force={force}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error destroying instance {instance_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/instances/{instance_id}/restart",
    response_model=CreateInstanceResponse,
    summary="重启浏览器实例",
    description="重启浏览器进程，保持相同端口和 user_data_dir 以恢复登录态",
)
async def restart_instance(instance_id: str) -> CreateInstanceResponse:
    """
    重启指定浏览器实例

    实例会被销毁后在同一端口重新启动，使用相同的 user_data_dir
    以保留 Cookie 和登录状态
    """
    try:
        instance = await pool.restart_instance(instance_id)

        return CreateInstanceResponse(
            instance_id=instance.instance_id,
            debug_port=instance.debug_port,
            ws_url=instance.ws_url,
            status=instance.status,
            browser_name=instance.browser_name,
            platform_name=instance.platform_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error restarting instance {instance_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================


@router.get(
    "/instances/{instance_id}/health",
    response_model=HealthCheckResponse,
    summary="单实例健康检查",
    description="检查指定浏览器实例的存活状态",
)
async def instance_health(instance_id: str) -> HealthCheckResponse:
    """
    检查单个实例的健康状态

    返回详细的健康信息，包括进程状态、端口连通性和 CDP 可用性
    """
    result = await pool.health_check_instance(instance_id)
    return HealthCheckResponse(**result)


@router.get(
    "/health",
    response_model=ServiceHealthResponse,
    summary="服务健康检查",
    description="返回 Browser-Service 整体健康状态",
)
async def service_health() -> ServiceHealthResponse:
    """
    服务整体健康检查
    """
    metrics = await pool.get_metrics()

    return ServiceHealthResponse(
        status="ok",
        version="1.0.0",
        instances_ready=metrics["ready"],
        instances_total=metrics["total_instances"],
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="运行时指标",
    description="返回 Browser-Service 运行时指标，包括实例统计和资源使用情况",
)
async def get_metrics() -> MetricsResponse:
    """
    获取运行时指标
    """
    metrics = await pool.get_metrics()

    return MetricsResponse(
        total_instances=metrics["total_instances"],
        ready=metrics["ready"],
        unhealthy=metrics["unhealthy"],
        starting=metrics["starting"],
        stopped=metrics["stopped"],
        port_range=metrics["port_range"],
        pool_size=metrics["pool_size"],
        system=metrics["system"],
        health_checker_uptime=health_checker.uptime if health_checker else 0,
        service_uptime=time.time() - service_start_time,
    )
