# -*- coding: utf-8 -*-
"""Pro 版 JSON/JSONL 存储 — 支持 homefeed + trending"""

from typing import Dict

from base.base_crawler import AbstractStore
from store.pro import AbstractStorePro
from tools.async_file_writer import AsyncFileWriter


class ProJsonStore(AbstractStore, AbstractStorePro):
    """Pro 版 JSON 存储"""

    def __init__(self, platform: str, crawler_type: str = "search", **kwargs):
        super().__init__()
        self.platform = platform
        self._crawler_type = crawler_type
        self.writer = AsyncFileWriter(platform=platform, crawler_type=crawler_type)

    async def store_content(self, content_item: Dict) -> None:
        if content_item:
            await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict) -> None:
        if comment_item:
            await self.writer.write_single_item_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator_item: Dict) -> None:
        if creator_item:
            await self.writer.write_single_item_to_json(item_type="creators", item=creator_item)

    async def store_homefeed(self, item: Dict) -> None:
        if item:
            await self.writer.write_single_item_to_json(item_type="homefeed", item=item)

    async def store_trending(self, item: Dict) -> None:
        if item:
            await self.writer.write_single_item_to_json(item_type="trending", item=item)

    async def flush(self) -> None:
        await self.writer.flush()

    async def close(self) -> None:
        await self.writer.close()


class ProJsonlStore(AbstractStore, AbstractStorePro):
    """Pro 版 JSONL 存储"""

    def __init__(self, platform: str, crawler_type: str = "search", **kwargs):
        super().__init__()
        self.platform = platform
        self._crawler_type = crawler_type
        self.writer = AsyncFileWriter(platform=platform, crawler_type=crawler_type)

    async def store_content(self, content_item: Dict) -> None:
        if content_item:
            await self.writer.write_single_item_to_json(item_type="contents", item=content_item, ensure_ascii=False)

    async def store_comment(self, comment_item: Dict) -> None:
        if comment_item:
            await self.writer.write_single_item_to_json(item_type="comments", item=comment_item, ensure_ascii=False)

    async def store_creator(self, creator_item: Dict) -> None:
        if creator_item:
            await self.writer.write_single_item_to_json(item_type="creators", item=creator_item, ensure_ascii=False)

    async def store_homefeed(self, item: Dict) -> None:
        if item:
            await self.writer.write_single_item_to_json(item_type="homefeed", item=item, ensure_ascii=False)

    async def store_trending(self, item: Dict) -> None:
        if item:
            await self.writer.write_single_item_to_json(item_type="trending", item=item, ensure_ascii=False)

    async def flush(self) -> None:
        await self.writer.flush()

    async def close(self) -> None:
        await self.writer.close()
