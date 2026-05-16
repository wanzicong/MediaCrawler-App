# -*- coding: utf-8 -*-
"""子进程按 task_id 从 MySQL 加载配置"""

from __future__ import annotations

from config.applier import apply_crawler_payload
from services.config_service import ConfigService


async def apply_task_config(task_id: int) -> None:
    payload = await ConfigService.get_task_payload(task_id)
    apply_crawler_payload(payload)
    await ConfigService.mark_task_running(task_id)
