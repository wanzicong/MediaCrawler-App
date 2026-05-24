# -*- coding: utf-8 -*-
"""配置方案与任务 — MySQL 持久化"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select, update, delete

from database.db_session import get_mysql_session
from database.system_models import CrawlerProfile, CrawlerTask


class ConfigService:

    @staticmethod
    def _default_payload() -> dict[str, Any]:
        return {
            "platform": "bilibili",
            "login_type": "qrcode",
            "crawler_type": "search",
            "keywords": "",
            "specified_ids": "",
            "creator_ids": "",
            "start_page": 1,
            "enable_comments": True,
            "enable_sub_comments": True,
            "save_option": "db",
            "cookies": "",
            "headless": True,
            "enable_cdp_mode": True,
            "cdp_headless": False,
            "enable_ip_proxy": False,
            "ip_proxy_pool_count": 2,
            "ip_proxy_provider_name": "kuaidaili",
            "crawler_max_notes_count": 100,
            "max_concurrency_num": 2,
            "crawler_max_comments_count_singlenotes": 1000,
            "crawler_max_sleep_sec": 5,
            "crawler_max_sleep_sec_max": 15,
            "enable_get_medias": False,
            "enable_get_wordcloud": False,
            "save_login_state": True,
            "xhs_international": False,
        }
    @staticmethod
    async def init_database() -> dict[str, str]:
        from database.db_session import create_tables

        await create_tables("db")
        await ConfigService.ensure_default_profile()
        return {"message": "数据库与系统表初始化完成"}

    @staticmethod
    async def ensure_default_profile() -> CrawlerProfile:
        async with get_mysql_session() as session:
            result = await session.execute(
                select(CrawlerProfile).where(CrawlerProfile.is_default.is_(True))
            )
            profile = result.scalar_one_or_none()
            if profile:
                return profile

            result = await session.execute(select(CrawlerProfile).limit(1))
            existing = result.scalar_one_or_none()
            if existing:
                return existing

            payload = ConfigService._default_payload()
            payload["save_option"] = "db"
            profile = CrawlerProfile(
                name="默认方案",
                description="系统初始方案，可在「配置方案」中修改",
                is_default=True,
                payload=payload,
            )
            session.add(profile)
            await session.flush()
            return profile

    @staticmethod
    async def list_profiles() -> list[dict]:
        async with get_mysql_session() as session:
            result = await session.execute(
                select(CrawlerProfile).order_by(
                    CrawlerProfile.is_default.desc(),
                    CrawlerProfile.id.asc(),
                )
            )
            rows = result.scalars().all()
            return [ConfigService._profile_to_dict(p) for p in rows]

    @staticmethod
    async def get_profile(profile_id: int) -> Optional[dict]:
        async with get_mysql_session() as session:
            profile = await session.get(CrawlerProfile, profile_id)
            return ConfigService._profile_to_dict(profile) if profile else None

    @staticmethod
    async def create_profile(
        name: str, payload: dict[str, Any], description: str = "", is_default: bool = False
    ) -> dict:
        payload = dict(payload)
        payload["save_option"] = "db"
        async with get_mysql_session() as session:
            if is_default:
                await session.execute(
                    update(CrawlerProfile).values(is_default=False)
                )
            profile = CrawlerProfile(
                name=name,
                description=description,
                is_default=is_default,
                payload=payload,
            )
            session.add(profile)
            await session.flush()
            return ConfigService._profile_to_dict(profile)

    @staticmethod
    async def update_profile(
        profile_id: int,
        name: Optional[str] = None,
        payload: Optional[dict] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> Optional[dict]:
        async with get_mysql_session() as session:
            profile = await session.get(CrawlerProfile, profile_id)
            if not profile:
                return None
            if is_default:
                await session.execute(
                    update(CrawlerProfile).values(is_default=False)
                )
            if name is not None:
                profile.name = name
            if description is not None:
                profile.description = description
            if payload is not None:
                p = dict(payload)
                p["save_option"] = "db"
                profile.payload = p
            if is_default is not None:
                profile.is_default = is_default
            profile.updated_at = datetime.utcnow()
            await session.flush()
            return ConfigService._profile_to_dict(profile)

    @staticmethod
    async def delete_profile(profile_id: int) -> bool:
        async with get_mysql_session() as session:
            profile = await session.get(CrawlerProfile, profile_id)
            if not profile:
                return False
            if profile.is_default:
                raise ValueError("不能删除默认方案，请先指定其他方案为默认")
            await session.delete(profile)
            return True

    @staticmethod
    async def set_default_profile(profile_id: int) -> Optional[dict]:
        return await ConfigService.update_profile(profile_id, is_default=True)

    @staticmethod
    async def get_default_payload() -> dict[str, Any]:
        async with get_mysql_session() as session:
            result = await session.execute(
                select(CrawlerProfile).where(CrawlerProfile.is_default.is_(True))
            )
            profile = result.scalar_one_or_none()
            if profile:
                return dict(profile.payload)
        return ConfigService._default_payload()

    @staticmethod
    def merge_payload(
        base: dict[str, Any], overrides: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        merged = dict(base)
        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    merged[k] = v
            # 同步 headless → cdp_headless（CDP 模式也使用无头配置）
            if "headless" in overrides:
                merged["cdp_headless"] = overrides["headless"]
        merged["save_option"] = "db"
        return merged

    @staticmethod
    async def create_task(
        payload: dict[str, Any], profile_id: Optional[int] = None
    ) -> dict:
        async with get_mysql_session() as session:
            task = CrawlerTask(
                profile_id=profile_id,
                status="pending",
                payload_snapshot=payload,
            )
            session.add(task)
            await session.flush()
            return ConfigService._task_to_dict(task)

    @staticmethod
    async def get_task(task_id: int) -> Optional[dict]:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            return ConfigService._task_to_dict(task) if task else None

    @staticmethod
    async def get_task_payload(task_id: int) -> dict[str, Any]:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            return dict(task.payload_snapshot)

    @staticmethod
    async def mark_task_running(task_id: int) -> None:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            if task:
                task.status = "running"
                task.started_at = datetime.utcnow()

    @staticmethod
    async def mark_task_finished(
        task_id: int, success: bool, error_message: Optional[str] = None
    ) -> None:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            if task:
                task.status = "completed" if success else "failed"
                task.finished_at = datetime.utcnow()
                task.error_message = error_message

    @staticmethod
    async def list_tasks(limit: int = 20) -> list[dict]:
        async with get_mysql_session() as session:
            result = await session.execute(
                select(CrawlerTask).order_by(CrawlerTask.id.desc()).limit(limit)
            )
            return [ConfigService._task_to_dict(t) for t in result.scalars().all()]

    @staticmethod
    async def list_tasks_paginated(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> dict:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        async with get_mysql_session() as session:
            count_stmt = select(func.count()).select_from(CrawlerTask)
            list_stmt = select(CrawlerTask).order_by(CrawlerTask.id.desc())

            if status:
                count_stmt = count_stmt.where(CrawlerTask.status == status)
                list_stmt = list_stmt.where(CrawlerTask.status == status)

            list_stmt = list_stmt.offset(offset).limit(page_size)

            total = (await session.execute(count_stmt)).scalar() or 0
            rows = (await session.execute(list_stmt)).scalars().all()

        return {
            "items": [ConfigService._task_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def update_task_progress(task_id: int, progress: dict) -> None:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            if task:
                task.progress = progress

    @staticmethod
    async def delete_task(task_id: int) -> bool:
        async with get_mysql_session() as session:
            task = await session.get(CrawlerTask, task_id)
            if not task:
                return False
            await session.delete(task)
            return True

    @staticmethod
    def _profile_to_dict(profile: CrawlerProfile) -> dict:
        return {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description or "",
            "is_default": profile.is_default,
            "payload": profile.payload,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    @staticmethod
    def _task_to_dict(task: CrawlerTask) -> dict:
        return {
            "id": task.id,
            "profile_id": task.profile_id,
            "status": task.status,
            "payload_snapshot": task.payload_snapshot,
            "error_message": task.error_message,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        }
