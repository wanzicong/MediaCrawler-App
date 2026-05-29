# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/crawler_manager.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import subprocess
import signal
import os
from typing import Any, Optional, List
from datetime import datetime
from pathlib import Path

import httpx

from ..schemas import CrawlerStartRequest, LogEntry

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class CrawlerManager:
    """Crawler process manager"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self.process: Optional[subprocess.Popen] = None
        self.status = "idle"
        self.started_at: Optional[datetime] = None
        self.current_config: Optional[CrawlerStartRequest] = None
        self.current_task_id: Optional[int] = None
        self._log_id = 0
        self._logs: List[LogEntry] = []
        self._read_task: Optional[asyncio.Task] = None
        # Project root directory
        self._project_root = Path(__file__).parent.parent.parent
        # Log queue - for pushing to WebSocket
        self._log_queue: Optional[asyncio.Queue] = None
        # Task queue for pending tasks when crawler is busy
        self._task_queue: List[dict] = []
        # Guard against concurrent start() calls (TOCTOU prevention)
        self._starting = False

    @property
    def logs(self) -> List[LogEntry]:
        return self._logs

    def get_log_queue(self) -> asyncio.Queue:
        """Get or create log queue"""
        if self._log_queue is None:
            self._log_queue = asyncio.Queue()
        return self._log_queue

    def _create_log_entry(self, message: str, level: str = "info") -> LogEntry:
        """Create log entry"""
        self._log_id += 1
        entry = LogEntry(
            id=self._log_id,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message
        )
        self._logs.append(entry)
        # Keep last 500 logs
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]
        return entry

    async def _push_log(self, entry: LogEntry):
        """Push log to queue"""
        if self._log_queue is not None:
            try:
                self._log_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _parse_log_level(self, line: str) -> str:
        """Parse log level"""
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
        """合并 payload，与 ConfigService.merge_payload 保持一致"""
        merged = dict(base)
        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    merged[k] = v
            if "headless" in overrides:
                merged["cdp_headless"] = overrides["headless"]
        # Docker 环境强制无头模式（Chrome 在容器中无法启动非无头窗口）
        if os.getenv("FORCE_CDP_HEADLESS"):
            merged["cdp_headless"] = True
            merged["headless"] = True
        merged["save_option"] = "db"
        return merged

    async def _create_task_via_api(self, config: CrawlerStartRequest) -> dict:
        """通过 Data API 创建任务记录，返回 {"task_id": task_id}"""
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
                pass  # 获取方案失败时使用默认配置

        overrides = config.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"profile_id"},
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
        """自动记录爬虫任务的关键词到 Data-API-Service 关键词管理模块。静默失败不影响主流程。"""
        keywords = (config.keywords or "").strip()
        platform = config.platform.value if hasattr(config.platform, 'value') else str(config.platform)

        if not keywords:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{DATA_API_URL}/api/keywords/auto-record",
                    json={
                        "platform": platform,
                        "keywords": keywords,
                        "task_id": task_id,
                    },
                )
        except Exception:
            pass

    async def _mark_task_finished_via_api(
        self, task_id: int, success: bool, error_message: str = ""
    ) -> None:
        """通过 Data API 标记任务完成或失败"""
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

    async def start(self, config: CrawlerStartRequest) -> dict:
        """Start crawler process or queue if busy. Returns {started, queued, task_id, queue_position}"""
        async with self._lock:
            if self._starting:
                return {"started": False, "queued": False, "error": "另一个启动请求正在处理中"}

            if self.process and self.process.poll() is None:
                # Busy: create task via API and queue it
                task = await self._create_task_via_api(config)
                self._task_queue.append({"task_id": task["task_id"], "config": config})
                # 自动记录关键词（异步，不阻塞排队流程）
                asyncio.create_task(self._auto_record_keywords(config, task["task_id"]))
                pos = len(self._task_queue)
                entry = self._create_log_entry(
                    f"Task #{task['task_id']} queued (position {pos}), crawler is busy",
                    "info",
                )
                await self._push_log(entry)
                return {"started": False, "queued": True, "task_id": task["task_id"], "queue_position": pos}

            self._starting = True

        try:
            # Cancel old log-reading task to avoid stdout competition
            if self._read_task and not self._read_task.done():
                self._read_task.cancel()
                try:
                    await self._read_task
                except asyncio.CancelledError:
                    pass
            self._read_task = None

            # Reap any zombie process
            if self.process and self.process.poll() is not None:
                self.process = None

            # Clear old logs
            self._logs = []
            self._log_id = 0

            # Clear pending queue (don't replace object to avoid WebSocket broadcast coroutine holding old queue reference)
            if self._log_queue is None:
                self._log_queue = asyncio.Queue()
            else:
                try:
                    while True:
                        self._log_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            task = await self._create_task_via_api(config)
            self.current_task_id = task["task_id"]

            # 自动记录关键词到关键词管理模块（异步，不阻塞爬虫启动）
            asyncio.create_task(self._auto_record_keywords(config, task["task_id"]))

            cmd = self._build_command(self.current_task_id)

            entry = self._create_log_entry(
                f"Starting crawler task #{self.current_task_id}: {' '.join(cmd)}",
                "info",
            )
            await self._push_log(entry)

            try:
                # Start subprocess
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    bufsize=1,
                    cwd=str(self._project_root),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"}
                )

                self.status = "running"
                self.started_at = datetime.now()
                self.current_config = config

                entry = self._create_log_entry(
                    f"Crawler started on platform: {config.platform.value}, type: {config.crawler_type.value}",
                    "success"
                )
                await self._push_log(entry)

                # Start log reading task
                self._read_task = asyncio.create_task(self._read_output())

                return {"started": True, "task_id": task["task_id"]}
            except Exception as e:
                self.status = "error"
                entry = self._create_log_entry(f"Failed to start crawler: {str(e)}", "error")
                await self._push_log(entry)
                return {"started": False, "queued": False, "error": str(e)}
        finally:
            async with self._lock:
                self._starting = False

    async def stop(self) -> bool:
        """Stop crawler process"""
        async with self._lock:
            if not self.process or self.process.poll() is not None:
                return False

            self.status = "stopping"
            stopping_process = self.process  # Save ref to avoid race with _dequeue_next
            entry = self._create_log_entry("Sending SIGTERM to crawler process...", "warning")
            await self._push_log(entry)

            try:
                stopping_process.send_signal(signal.SIGTERM)

                # Wait for graceful exit (up to 15 seconds)
                for _ in range(30):
                    if stopping_process.poll() is not None:
                        break
                    await asyncio.sleep(0.5)

                # If still not exited, force kill
                if stopping_process.poll() is None:
                    entry = self._create_log_entry("Process not responding, sending SIGKILL...", "warning")
                    await self._push_log(entry)
                    stopping_process.kill()

                entry = self._create_log_entry("Crawler process terminated", "info")
                await self._push_log(entry)

            except Exception as e:
                entry = self._create_log_entry(f"Error stopping crawler: {str(e)}", "error")
                await self._push_log(entry)

            # Only reset to idle if no new process was dequeued while we were waiting
            if self.process is stopping_process or self.process is None:
                self.status = "idle"
                self.current_config = None
                self.current_task_id = None
                self.started_at = None

                # Cancel log reading task
                if self._read_task:
                    self._read_task.cancel()
                    self._read_task = None

            return True

    def get_status(self) -> dict:
        """Get current status"""
        # Auto-correct: if status says running but process is dead, reset to idle
        if self.status in ("running", "stopping"):
            if self.process and self.process.poll() is not None:
                self.status = "idle"
                self.current_task_id = None
            elif not self.process and self.status != "idle":
                self.status = "idle"
                self.current_task_id = None

        return {
            "status": self.status,
            "platform": self.current_config.platform.value if self.current_config else None,
            "crawler_type": self.current_config.crawler_type.value if self.current_config else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error_message": None,
            "task_id": self.current_task_id,
            "queue_length": len(self._task_queue),
        }

    def _build_command(self, task_id: int) -> list:
        """通过 task_id 从 MySQL 加载配置并启动爬虫"""
        import sys as _sys
        python_exe = _sys.executable  # 使用当前 Python 解释器路径
        return [python_exe, "main.py", "--task-id", str(task_id)]

    async def _dequeue_next(self):
        """Start next queued task if any"""
        if not self._task_queue:
            return
        pending = self._task_queue.pop(0)
        task_id = pending["task_id"]
        self.current_task_id = task_id
        cmd = self._build_command(task_id)

        entry = self._create_log_entry(
            f"Starting queued task #{task_id} ({len(self._task_queue)} remaining): {' '.join(cmd)}",
            "info",
        )
        await self._push_log(entry)

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                cwd=str(self._project_root),
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            self.status = "running"
            self.started_at = datetime.now()
            self.current_config = pending["config"]
            entry = self._create_log_entry(
                f"Queued task #{task_id} started",
                "success"
            )
            await self._push_log(entry)
            self._read_task = asyncio.create_task(self._read_output())
        except Exception as e:
            self.status = "error"
            entry = self._create_log_entry(f"Failed to start queued task #{task_id}: {str(e)}", "error")
            await self._push_log(entry)
            await self._mark_task_finished_via_api(task_id, False, f"Failed to start: {str(e)}")

    async def _read_output(self):
        """Asynchronously read process output"""
        loop = asyncio.get_event_loop()

        async def _monitor_process():
            """Monitor that process is alive; trigger recovery if it dies unexpectedly"""
            while self.process and self.process.poll() is None:
                await asyncio.sleep(5)
            if self.status == "running":
                exit_code = self.process.returncode if self.process else -1
                entry = self._create_log_entry(
                    f"[Monitor] Process exited with code {exit_code}, triggering recovery",
                    "warning"
                )
                await self._push_log(entry)
                # Close stdout to unblock readline() in the main read loop
                if self.process and self.process.stdout:
                    try:
                        self.process.stdout.close()
                    except Exception:
                        pass

        monitor_task: Optional[asyncio.Task] = None

        try:
            monitor_task = asyncio.create_task(_monitor_process())

            while self.process and self.process.poll() is None:
                try:
                    line = await asyncio.wait_for(
                        loop.run_in_executor(None, self.process.stdout.readline),
                        timeout=10.0
                    )
                    if line:
                        line = line.strip()
                        if line:
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line, level)
                            await self._push_log(entry)
                except asyncio.TimeoutError:
                    # No output for 10s; check if process still alive
                    if self.process and self.process.poll() is not None:
                        break
                    continue

            # Cancel monitor since process already exited
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

            # Read remaining output
            if self.process and self.process.stdout:
                remaining = await loop.run_in_executor(
                    None, self.process.stdout.read
                )
                if remaining:
                    for line in remaining.strip().split('\n'):
                        if line.strip():
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line.strip(), level)
                            await self._push_log(entry)

            if self.status in ("running", "stopping"):
                exit_code = self.process.returncode if self.process else -1
                success = exit_code == 0 and self.status == "running"
                if success:
                    entry = self._create_log_entry("Crawler completed successfully", "success")
                else:
                    entry = self._create_log_entry(f"Crawler exited with code: {exit_code}", "warning")
                await self._push_log(entry)
                if self.current_task_id:
                    await self._mark_task_finished_via_api(
                        self.current_task_id,
                        success,
                        "" if success else f"exit code {exit_code}",
                    )
                self.status = "idle"
                self.current_task_id = None
                # Check for queued tasks (skip if stop() is running to avoid race)
                if self._task_queue and not self._lock.locked():
                    await self._dequeue_next()

        except asyncio.CancelledError:
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            if self.current_task_id:
                await self._mark_task_finished_via_api(
                    self.current_task_id, False, "Manager interrupted"
                )
            self.status = "idle"
            self.current_task_id = None
            # Check for queued tasks even when cancelled (e.g., user called stop())
            if self._task_queue:
                await self._dequeue_next()
            raise
        except Exception as e:
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            entry = self._create_log_entry(f"Error reading output: {str(e)}", "error")
            await self._push_log(entry)
            # Ensure status is reset even on unexpected errors
            if self.status == "running":
                if self.current_task_id and self.process and self.process.poll() is not None:
                    await self._mark_task_finished_via_api(
                        self.current_task_id,
                        False,
                        f"Manager error: {str(e)}",
                    )
                self.status = "idle"
                self.current_task_id = None
                # Check for queued tasks on error too
                if self._task_queue:
                    await self._dequeue_next()


# Global singleton
crawler_manager = CrawlerManager()
