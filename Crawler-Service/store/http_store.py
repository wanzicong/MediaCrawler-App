# -*- coding: utf-8 -*-
"""HTTP Store — 通过 HTTP 调用 Data-API-Service 内部 API 持久化数据，替代 SQLAlchemy 直连 MySQL"""

import os
from typing import Dict

import httpx

from base.base_crawler import AbstractStore

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class HttpStore(AbstractStore):
    """通用 HTTP Store 基类，通过 Data-API-Service 内部 API 写入数据"""

    def __init__(self, platform: str):
        super().__init__()
        self.platform = platform
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    @staticmethod
    def _get_task_id() -> int | None:
        import config
        return getattr(config, 'TASK_ID', None)

    async def store_content(self, content_item: Dict):
        if not content_item:
            return
        await self._batch_store("content", [content_item])

    async def store_comment(self, comment_item: Dict):
        if not comment_item:
            return
        await self._batch_store("comment", [comment_item])

    async def store_creator(self, creator_item: Dict):
        if not creator_item:
            return
        await self._batch_store("creator", [creator_item])

    async def _batch_store(self, kind: str, records: list[Dict]):
        if not records:
            return
        client = self._get_client()
        task_id = self._get_task_id()
        resp = await client.post(
            f"{DATA_API_URL}/api/internal/data/batch",
            json={
                "platform": self.platform,
                "kind": kind,
                "task_id": task_id,
                "records": records,
            },
        )
        resp.raise_for_status()

    async def flush_all(self, items_by_kind: dict[str, list[Dict]]):
        """批量 flush，每个 kind 发送一次 HTTP 请求"""
        for kind, records in items_by_kind.items():
            if records:
                await self._batch_store(kind, records)

    async def close(self):
        if self._client:
            await self._client.aclose()
