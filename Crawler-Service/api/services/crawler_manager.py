# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/crawler_manager.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

import asyncio
import subprocess
import signal
import os
from typing import Any, Optional, List, Dict, Union
from datetime import datetime
from pathlib import Path

import httpx

from ..schemas import CrawlerStartRequest, LogEntry

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")

# 平台风控并发约束：同一平台最多同时运行的爬虫数
PLATFORM_CONCURRENCY = {
    "xhs": 1, "dy": 1, "ks": 2, "bili": 3,
    "wb": 2, "tieba": 3, "zhihu": 3,
}


class CrawlerManager:
    """多进程爬虫管理器 — 支持同时运行多个爬虫任务"""

    MAX_CONCURRENT = 3  # 全局最大并发数

    def __init__(self):
        self._lock = asyncio.Lock()
        # 运行中的进程池: task_id -> {process, config, started_at, read_task}
        self._processes: Dict[int, dict] = {}
        self._platform_running: Dict[str, int] = {}  # platform -> count
        self._log_id = 0
        self._logs: List[LogEntry] = []
        self._log_queue: Optional[asyncio.Queue] = None
        self._task_queue: List[dict] = []
        self._starting = False
        self._project_root = Path(__file__).parent.parent.parent

    @property
    def logs(self) -> List[LogEntry]:
        return self._logs

    @property
    def running_count(self) -> int:
        return len(self._processes)

    def get_log_queue(self) -> asyncio.Queue:
        if self._log_queue is None:
            self._log_queue = asyncio.Queue()
        return self._log_queue

    def _create_log_entry(self, message: str, level: str = "info", task_id: Optional[int] = None) -> LogEntry:
        self._log_id += 1
        entry = LogEntry(
            id=self._log_id,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=f"[Task #{task_id}] {message}" if task_id else message,
        )
        self._logs.append(entry)
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]
        return entry

    async def _push_log(self, entry: LogEntry):
        if self._log_queue is not None:
            try:
                self._log_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _parse_log_level(self, line: str) -> str:
        line_upper = line.upper()
        if "ERROR" in line_upper or "FAILED" in line_upper:
            return "error"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            return "warning"
        elif "SUCCESS" in line_upper or "完成" in line or "成功" in line:
            return "success"
        elif "DEBUG" in line_upper:
            return "debug"
        return "info"

    @staticmethod
    def _merge_payload(base: dict, overrides: Optional[dict] = None) -> dict:
        merged = dict(base)
        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    merged[k] = v
            if "headless" in overrides:
                merged["cdp_headless"] = overrides["headless"]
        if os.getenv("FORCE_CDP_HEADLESS"):
            merged["cdp_headless"] = True
            merged["headless"] = True
        merged["save_option"] = "db"
        return merged

    def _can_start_platform(self, platform: str) -> bool:
        """检查平台是否还能启动新任务"""
        limit = PLATFORM_CONCURRENCY.get(platform, 2)
        return self._platform_running.get(platform, 0) < limit

    def _can_start_any(self) -> bool:
        return self.running_count < self.MAX_CONCURRENT

    async def _create_task_via_api(self, config: CrawlerStartRequest) -> dict:
        from config.profile_defaults import build_default_payload

        base_payload = build_default_payload()
        if config.profile_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{DATA_API_URL}/api/internal/profiles/{config.profile_id}"
                    )
                    if resp.status_code == 200:
                        profile = resp.json()
                        base_payload = profile["payload"]
            except Exception:
                pass

        overrides = config.model_dump(
            mode="json", exclude_none=True, exclude={"profile_id"},
        )
        for k, v in overrides.items():
            if hasattr(v, "value"):
                overrides[k] = v.value
        payload = self._merge_payload(base_payload, overrides)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{DATA_API_URL}/api/internal/tasks",
                json={"payload": payload, "profile_id": config.profile_id},
            )
            resp.raise_for_status()
            return resp.json()

    async def _auto_record_keywords(self, config, task_id: int) -> None:
        keywords = (config.keywords or "").strip()
        platform = config.platform.value if hasattr(config.platform, 'value') else str(config.platform)
        if not keywords:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{DATA_API_URL}/api/keywords/auto-record",
                    json={"platform": platform, "keywords": keywords, "task_id": task_id},
                )
        except Exception:
            pass

    async def _mark_task_finished_via_api(
        self, task_id: int, success: bool, error_message: str = ""
    ) -> None:
        status = "completed" if success else "failed"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.put(
                    f"{DATA_API_URL}/api/internal/tasks/{task_id}/finish",
                    json={"status": status, "error": error_message},
                )
                resp.raise_for_status()
                entry = self._create_log_entry(
                    f"Task #{task_id} marked as {status} in DB", "info"
                )
                await self._push_log(entry)
        except Exception as e:
            entry = self._create_log_entry(
                f"Failed to mark task #{task_id} as {status}: {e}", "error"
            )
            await self._push_log(entry)

    def _build_command(self, task_id: int) -> list:
        import sys as _sys
        return [_sys.executable, "main.py", "--task-id", str(task_id)]

    async def start(self, config: CrawlerStartRequest) -> dict:
        """启动爬虫任务（支持并发，超出上限则排队）"""
        platform = config.platform.value if hasattr(config.platform, 'value') else str(config.platform)

        async with self._lock:
            if self._starting:
                return {"started": False, "queued": False, "error": "另一个启动请求正在处理中"}

            # 先创建任务记录
            task_record = await self._create_task_via_api(config)
            task_id = task_record["task_id"]
            asyncio.create_task(self._auto_record_keywords(config, task_id))

            # 仅创建不执行
            if not config.execute_now:
                return {"started": False, "queued": False, "task_id": task_id, "created": True}

            # 检查是否达到并发上限
            if not self._can_start_any():
                self._task_queue.append({"task_id": task_id, "config": config})
                pos = len(self._task_queue)
                entry = self._create_log_entry(
                    f"Task #{task_id} queued (position {pos}, global limit {self.MAX_CONCURRENT} reached)", "info"
                )
                await self._push_log(entry)
                return {"started": False, "queued": True, "task_id": task_id, "queue_position": pos}

            if not self._can_start_platform(platform):
                self._task_queue.append({"task_id": task_id, "config": config})
                pos = len(self._task_queue)
                entry = self._create_log_entry(
                    f"Task #{task_id} queued (position {pos}, platform '{platform}' limit reached)", "info"
                )
                await self._push_log(entry)
                return {"started": False, "queued": True, "task_id": task_id, "queue_position": pos}

            # 预占槽位（原子性），防止 TOCTOU 竞态
            placeholder = {"task_id": task_id, "platform": platform, "_reserved": True}
            self._processes[task_id] = placeholder
            self._platform_running[platform] = self._platform_running.get(platform, 0) + 1
            self._starting = True

        try:
            return await self._do_start(task_id, config)
        except Exception:
            async with self._lock:
                self._processes.pop(task_id, None)
                if self._platform_running.get(platform, 0) > 0:
                    self._platform_running[platform] -= 1
            raise
        finally:
            async with self._lock:
                self._starting = False

    async def _do_start(self, task_id: int, config: CrawlerStartRequest) -> dict:
        """实际启动子进程。调用者已预占槽位，此处替换占位符。"""
        platform = config.platform.value if hasattr(config.platform, 'value') else str(config.platform)
        cmd = self._build_command(task_id)

        entry = self._create_log_entry(
            f"Starting crawler task #{task_id}: {' '.join(cmd)}", "info", task_id
        )
        await self._push_log(entry)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', bufsize=1,
                cwd=str(self._project_root),
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            read_task = asyncio.create_task(self._read_output(proc, task_id))

            # 替换预占的占位符为真实进程数据
            self._processes[task_id] = {
                "process": proc,
                "config": config,
                "started_at": datetime.now(),
                "read_task": read_task,
                "platform": platform,
            }

            entry = self._create_log_entry(
                f"Crawler started [{self.running_count}/{self.MAX_CONCURRENT}] on platform: {platform}, type: {config.crawler_type.value}",
                "success", task_id
            )
            await self._push_log(entry)
            return {"started": True, "task_id": task_id, "running_count": self.running_count}

        except Exception as e:
            entry = self._create_log_entry(f"Failed to start crawler: {str(e)}", "error", task_id)
            await self._push_log(entry)
            await self._mark_task_finished_via_api(task_id, False, str(e))
            return {"started": False, "queued": False, "error": str(e)}

    async def execute_task(self, task_id: int) -> dict:
        """执行一个待执行的任务"""
        async with self._lock:
            if self._starting:
                return {"started": False, "error": "另一个启动请求正在处理中"}

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{DATA_API_URL}/api/internal/tasks/{task_id}")
                    if resp.status_code != 200:
                        return {"started": False, "error": f"任务 #{task_id} 不存在"}
                    task_data = resp.json()
            except Exception as e:
                return {"started": False, "error": str(e)}

            if task_data.get("status") not in ("pending", "failed"):
                return {"started": False, "error": f"任务状态为 {task_data.get('status')}，无法执行"}

            payload = task_data.get("payload_snapshot", {})
            platform = payload.get("platform", "xhs")

            if not self._can_start_any():
                return {"started": False, "error": f"已达全局并发上限 ({self.MAX_CONCURRENT})"}

            if not self._can_start_platform(platform):
                return {"started": False, "error": f"平台 '{platform}' 已达并发上限"}

            self._starting = True

        try:
            cmd = self._build_command(task_id)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', bufsize=1,
                cwd=str(self._project_root),
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            read_task = asyncio.create_task(self._read_output(proc, task_id))

            from ..schemas import CrawlerStartRequest as CSR
            cfg = CSR(**{k: v for k, v in payload.items() if k in CSR.model_fields})

            self._processes[task_id] = {
                "process": proc, "config": cfg, "started_at": datetime.now(),
                "read_task": read_task, "platform": platform,
            }
            self._platform_running[platform] = self._platform_running.get(platform, 0) + 1

            entry = self._create_log_entry(f"Pending task #{task_id} started", "success", task_id)
            await self._push_log(entry)
            return {"started": True, "task_id": task_id}
        except Exception as e:
            entry = self._create_log_entry(f"Failed to execute task #{task_id}: {str(e)}", "error", task_id)
            await self._push_log(entry)
            await self._mark_task_finished_via_api(task_id, False, str(e))
            return {"started": False, "error": str(e)}
        finally:
            async with self._lock:
                self._starting = False

    async def stop(self, task_id: Optional[int] = None) -> dict:
        """停止爬虫进程。task_id=None 停止所有，否则停止指定任务"""
        to_kill: List[tuple] = []

        async with self._lock:
            if task_id is not None:
                pinfo = self._processes.get(task_id)
                if not pinfo:
                    return {"stopped": False, "error": f"Task #{task_id} not running"}
                to_kill.append((task_id, pinfo))
            else:
                self._task_queue.clear()  # 防止 stop 后任务自动重启
                for tid in list(self._processes.keys()):
                    to_kill.append((tid, self._processes[tid]))

        # 在锁外杀进程，不阻塞其他 API 操作
        for tid, pinfo in to_kill:
            await self._kill_process(pinfo, tid)

            async with self._lock:
                self._cleanup_task(tid)

        return {"stopped": True, "task_ids": [t[0] for t in to_kill]}

    async def _kill_process(self, pinfo: dict, task_id: int):
        """终止单个进程"""
        proc = pinfo["process"]
        if proc.poll() is not None:
            self._cleanup_task(task_id)
            return

        entry = self._create_log_entry("Sending SIGTERM...", "warning", task_id)
        await self._push_log(entry)

        try:
            proc.send_signal(signal.SIGTERM)
            for _ in range(30):
                if proc.poll() is not None:
                    break
                await asyncio.sleep(0.5)
            if proc.poll() is None:
                entry = self._create_log_entry("Force killing...", "warning", task_id)
                await self._push_log(entry)
                proc.kill()
            entry = self._create_log_entry("Process terminated", "info", task_id)
            await self._push_log(entry)
        except Exception as e:
            entry = self._create_log_entry(f"Error stopping: {str(e)}", "error", task_id)
            await self._push_log(entry)

        self._cleanup_task(task_id)

    def _cleanup_task(self, task_id: int):
        """清理任务状态"""
        pinfo = self._processes.pop(task_id, None)
        if pinfo:
            platform = pinfo.get("platform", "")
            if platform and self._platform_running.get(platform, 0) > 0:
                self._platform_running[platform] -= 1
            if pinfo.get("read_task") and not pinfo["read_task"].done():
                pinfo["read_task"].cancel()

    def get_status(self) -> dict:
        """获取当前状态（兼容旧接口，增加 running_tasks 列表）"""
        running_tasks = []
        for tid, pinfo in self._processes.items():
            cfg = pinfo.get("config")
            running_tasks.append({
                "task_id": tid,
                "platform": cfg.platform.value if cfg and hasattr(cfg, 'platform') else pinfo.get("platform"),
                "crawler_type": cfg.crawler_type.value if cfg and hasattr(cfg, 'crawler_type') else None,
                "started_at": pinfo["started_at"].isoformat() if pinfo["started_at"] else None,
                "status": "running",
            })

        is_active = self.running_count > 0
        first_task = running_tasks[0] if running_tasks else None

        return {
            "status": "running" if is_active else "idle",
            "platform": first_task["platform"] if first_task else None,
            "crawler_type": first_task["crawler_type"] if first_task else None,
            "started_at": first_task["started_at"] if first_task else None,
            "error_message": None,
            "task_id": first_task["task_id"] if first_task else None,
            "queue_length": len(self._task_queue),
            "running_count": self.running_count,
            "max_concurrent": self.MAX_CONCURRENT,
            "running_tasks": running_tasks,
        }

    async def _read_output(self, proc: subprocess.Popen, task_id: int):
        """读取单个子进程的输出"""
        loop = asyncio.get_event_loop()

        async def _monitor():
            while proc.poll() is None:
                await asyncio.sleep(5)
            # 进程已退出，readline 会自然收到 EOF，不需主动 close

        monitor_task: Optional[asyncio.Task] = None
        try:
            monitor_task = asyncio.create_task(_monitor())

            while proc.poll() is None:
                try:
                    line = await asyncio.wait_for(
                        loop.run_in_executor(None, proc.stdout.readline),
                        timeout=10.0
                    )
                    if line:
                        line = line.strip()
                        if line:
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line, level, task_id)
                            await self._push_log(entry)
                except asyncio.TimeoutError:
                    if proc.poll() is not None:
                        break
                    continue

            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

            # Drain剩余输出（容错：pipe 可能已被 OS 关闭）
            if proc.stdout:
                try:
                    remaining = await loop.run_in_executor(None, proc.stdout.read)
                    if remaining:
                        for line in remaining.strip().split('\n'):
                            if line.strip():
                                level = self._parse_log_level(line)
                                entry = self._create_log_entry(line.strip(), level, task_id)
                                await self._push_log(entry)
                except (ValueError, OSError):
                    pass  # pipe 已关闭，正常情况

            exit_code = proc.returncode or -1
            success = exit_code == 0
            if success:
                entry = self._create_log_entry("Crawler completed successfully", "success", task_id)
            else:
                entry = self._create_log_entry(f"Crawler exited with code: {exit_code}", "warning", task_id)
            await self._push_log(entry)
            await self._mark_task_finished_via_api(task_id, success, "" if success else f"exit code {exit_code}")

        except asyncio.CancelledError:
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            await self._mark_task_finished_via_api(task_id, False, "Manager interrupted")
            raise
        except Exception as e:
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            entry = self._create_log_entry(f"Error reading output: {str(e)}", "error", task_id)
            await self._push_log(entry)
            await self._mark_task_finished_via_api(task_id, False, f"Manager error: {str(e)}")
        finally:
            self._cleanup_task(task_id)
            # 自动启动排队任务
            async with self._lock:
                if self._task_queue:
                    await self._dequeue_next()

    async def _dequeue_next(self):
        """启动下一个排队任务（需在 lock 内调用）"""
        while self._task_queue and self._can_start_any():
            pending = self._task_queue.pop(0)
            tid = pending["task_id"]
            cfg = pending["config"]
            platform = cfg.platform.value if hasattr(cfg, 'platform') else str(cfg.platform)

            if not self._can_start_platform(platform):
                self._task_queue.insert(0, pending)
                for i, p in enumerate(self._task_queue[1:], 1):
                    p2_platform = p["config"].platform.value if hasattr(p["config"], 'platform') else str(p["config"].platform)
                    if self._can_start_platform(p2_platform):
                        self._task_queue.pop(i)
                        result = await self._do_start(p["task_id"], p["config"])
                        if not result.get("started"):
                            self._task_queue.insert(0, p)  # 失败重新排队
                        return
                return

            result = await self._do_start(tid, cfg)
            if not result.get("started"):
                self._task_queue.insert(0, pending)  # 失败重新排队


# Global singleton
crawler_manager = CrawlerManager()
