# -*- coding: utf-8 -*-
"""Pro 版 HTTP 存储 — 通过 Data-API 写入数据库，支持 homefeed + trending"""

from typing import Dict

from store.http_store import HttpStore
from store.pro import AbstractStorePro


class ProHttpStore(HttpStore, AbstractStorePro):
    """Pro 版 DB 存储，在 HttpStore 基础上增加 homefeed/trending 写入"""

    async def store_homefeed(self, item: Dict) -> None:
        if not item:
            return
        await self._batch_store("homefeed", [item])

    async def store_trending(self, item: Dict) -> None:
        if not item:
            return
        await self._batch_store("trending", [item])

    async def flush(self) -> None:
        pass

    async def close(self) -> None:
        await HttpStore.close(self)
