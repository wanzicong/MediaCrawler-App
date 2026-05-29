# -*- coding: utf-8 -*-
"""
断点续爬管理器

支持页级别、笔记级别、评论级别的断点保存与恢复。
任务中断后可从上一次进度继续，避免重复爬取。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")
CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", Path(__file__).parent.parent / "checkpoints"))


@dataclass
class Checkpoint:
    """爬取进度快照"""
    task_id: int
    platform: str
    crawler_type: str
    keywords: str = ""

    # 搜索模式进度
    current_page: int = 1
    crawled_note_ids: Set[str] = field(default_factory=set)
    total_crawled: int = 0

    # 游标翻页进度
    last_cursor: Optional[str] = None
    last_note_time: Optional[int] = None

    # 评论爬取进度: {note_id: 已爬评论数}
    comment_progress: Dict[str, int] = field(default_factory=dict)

    # 创作者模式进度
    creator_crawled_count: int = 0

    # 元信息
    created_at: float = 0.0
    updated_at: float = 0.0
    status: str = "running"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["crawled_note_ids"] = list(self.crawled_note_ids)
        d.pop("created_at", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        data_copy = dict(data)
        data_copy["crawled_note_ids"] = set(data_copy.get("crawled_note_ids", []))
        data_copy["created_at"] = data_copy.get("created_at", 0.0)
        return cls(**{k: v for k, v in data_copy.items() if k in cls.__dataclass_fields__})


class CheckpointManager:
    """断点续爬管理器"""

    def __init__(self, task_id: int, platform: str, crawler_type: str):
        self._checkpoint: Optional[Checkpoint] = None
        self._task_id = task_id
        self._platform = platform
        self._crawler_type = crawler_type
        self._last_save_time = 0.0
        self._min_save_interval = 5  # 最小保存间隔(秒)

        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self._local_path = CHECKPOINT_DIR / f"checkpoint_{task_id}.json"

    async def init(self, keywords: str = "") -> Checkpoint:
        """初始化检查点：优先本地恢复，其次远程恢复，最后新建"""
        restored = await self._try_restore_local()
        if restored:
            self._checkpoint = restored
            return restored

        restored = await self._try_restore_remote()
        if restored:
            self._checkpoint = restored
            return restored

        now = time.time()
        self._checkpoint = Checkpoint(
            task_id=self._task_id,
            platform=self._platform,
            crawler_type=self._crawler_type,
            keywords=keywords,
            created_at=now,
            updated_at=now,
        )
        await self._save()
        return self._checkpoint

    async def save(self) -> None:
        await self._save()

    async def try_save(self) -> None:
        now = time.time()
        if now - self._last_save_time >= self._min_save_interval:
            await self._save()

    @property
    def cp(self) -> Checkpoint:
        if self._checkpoint is None:
            raise RuntimeError("CheckpointManager not initialized")
        return self._checkpoint

    def mark_page_done(self, page: int, note_ids: List[str]) -> None:
        self.cp.current_page = page
        self.cp.crawled_note_ids.update(note_ids)
        self.cp.total_crawled = len(self.cp.crawled_note_ids)
        self.cp.updated_at = time.time()

    def set_cursor(self, cursor: str, note_time: int = 0) -> None:
        self.cp.last_cursor = cursor
        if note_time > 0:
            self.cp.last_note_time = note_time
        self.cp.updated_at = time.time()

    def mark_note_crawled(self, note_id: str) -> None:
        self.cp.crawled_note_ids.add(note_id)
        self.cp.total_crawled = len(self.cp.crawled_note_ids)
        self.cp.updated_at = time.time()

    def set_comment_progress(self, note_id: str, count: int) -> None:
        self.cp.comment_progress[note_id] = count
        self.cp.updated_at = time.time()

    def mark_creator_done(self, count: int) -> None:
        self.cp.creator_crawled_count = count
        self.cp.updated_at = time.time()

    def mark_completed(self) -> None:
        self.cp.status = "completed"
        self.cp.updated_at = time.time()

    def is_note_crawled(self, note_id: str) -> bool:
        return note_id in self.cp.crawled_note_ids

    def get_comment_progress(self, note_id: str) -> int:
        return self.cp.comment_progress.get(note_id, 0)

    async def _save(self) -> None:
        now = time.time()
        self.cp.updated_at = now
        self._last_save_time = now

        data = self.cp.to_dict()
        data["updated_at"] = now

        try:
            self._local_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(
                    f"{DATA_API_URL}/api/internal/tasks/{self._task_id}/checkpoint",
                    json=data,
                )
        except Exception:
            pass

    async def _try_restore_local(self) -> Optional[Checkpoint]:
        if not self._local_path.exists():
            return None
        try:
            data = json.loads(self._local_path.read_text(encoding="utf-8"))
            cp = Checkpoint.from_dict(data)
            if cp.status == "running":
                print(f"[Checkpoint] 从本地恢复进度: #{self._task_id}"
                      f" 已爬={cp.total_crawled} 页={cp.current_page}")
            return cp
        except Exception:
            return None

    async def _try_restore_remote(self) -> Optional[Checkpoint]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DATA_API_URL}/api/internal/tasks/{self._task_id}/checkpoint"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("status") == "running":
                        cp = Checkpoint.from_dict(data)
                        print(f"[Checkpoint] 从远程恢复进度: #{self._task_id}"
                              f" 已爬={cp.total_crawled} 页={cp.current_page}")
                        return cp
        except Exception:
            pass
        return None

