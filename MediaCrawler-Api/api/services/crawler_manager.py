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
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from ..schemas import CrawlerStartRequest, LogEntry


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

    async def start(self, config: CrawlerStartRequest) -> dict:
        """Start crawler process or queue if busy. Returns {started, queued, task_id, queue_position}"""
        async with self._lock:
            if self._starting:
                return {"started": False, "queued": False, "error": "另一个启动请求正在处理中"}

            if self.process and self.process.poll() is None:
                # Busy: create task and queue it
                from services.config_service import ConfigService

                base_payload = await ConfigService.get_default_payload()
                if config.profile_id:
                    profile = await ConfigService.get_profile(config.profile_id)
                    if profile:
                        base_payload = profile["payload"]

                overrides = config.model_dump(
                    mode="json",
                    exclude_none=True,
                    exclude={"profile_id"},
                )
                for k, v in overrides.items():
                    if hasattr(v, "value"):
                        overrides[k] = v.value
                payload = ConfigService.merge_payload(base_payload, overrides)
                task = await ConfigService.create_task(payload, config.profile_id)
                self._task_queue.append({"task_id": task["id"], "config": config})
                pos = len(self._task_queue)
                entry = self._create_log_entry(
                    f"Task #{task['id']} queued (position {pos}), crawler is busy",
                    "info",
                )
                await self._push_log(entry)
                return {"started": False, "queued": True, "task_id": task["id"], "queue_position": pos}

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

            from services.config_service import ConfigService

            base_payload = await ConfigService.get_default_payload()
            if config.profile_id:
                profile = await ConfigService.get_profile(config.profile_id)
                if profile:
                    base_payload = profile["payload"]

            overrides = config.model_dump(
                mode="json",
                exclude_none=True,
                exclude={"profile_id"},
            )
            for k, v in overrides.items():
                if hasattr(v, "value"):
                    overrides[k] = v.value
            payload = ConfigService.merge_payload(base_payload, overrides)
            task = await ConfigService.create_task(payload, config.profile_id)
            self.current_task_id = task["id"]

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

                return {"started": True, "task_id": task["id"]}
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
            entry = self._create_log_entry("Sending SIGTERM to crawler process...", "warning")
            await self._push_log(entry)

            try:
                self.process.send_signal(signal.SIGTERM)

                # Wait for graceful exit (up to 15 seconds)
                for _ in range(30):
                    if self.process.poll() is not None:
                        break
                    await asyncio.sleep(0.5)

                # If still not exited, force kill
                if self.process.poll() is None:
                    entry = self._create_log_entry("Process not responding, sending SIGKILL...", "warning")
                    await self._push_log(entry)
                    self.process.kill()

                entry = self._create_log_entry("Crawler process terminated", "info")
                await self._push_log(entry)

            except Exception as e:
                entry = self._create_log_entry(f"Error stopping crawler: {str(e)}", "error")
                await self._push_log(entry)

            self.status = "idle"
            self.current_config = None
            self.current_task_id = None

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
        return ["uv", "run", "python", "main.py", "--task-id", str(task_id)]

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
            from services.config_service import ConfigService
            try:
                await ConfigService.mark_task_finished(task_id, False, f"Failed to start: {str(e)}")
            except Exception:
                pass

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

            if self.status == "running":
                exit_code = self.process.returncode if self.process else -1
                success = exit_code == 0
                if success:
                    entry = self._create_log_entry("Crawler completed successfully", "success")
                else:
                    entry = self._create_log_entry(f"Crawler exited with code: {exit_code}", "warning")
                await self._push_log(entry)
                if self.current_task_id:
                    from services.config_service import ConfigService

                    await ConfigService.mark_task_finished(
                        self.current_task_id,
                        success,
                        None if success else f"exit code {exit_code}",
                    )
                self.status = "idle"
                self.current_task_id = None
                # Check for queued tasks
                if self._task_queue:
                    await self._dequeue_next()

        except asyncio.CancelledError:
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            if self.current_task_id:
                from services.config_service import ConfigService
                try:
                    await ConfigService.mark_task_finished(
                        self.current_task_id, False, "Manager interrupted"
                    )
                except Exception:
                    pass
            self.status = "idle"
            self.current_task_id = None
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
                    from services.config_service import ConfigService
                    await ConfigService.mark_task_finished(
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
