# -*- coding: utf-8 -*-
"""Pro 版 Excel 存储 — 支持 homefeed + trending"""

from typing import Dict

from store.excel_store_base import ExcelStoreBase
from store.pro import AbstractStorePro


class ProExcelStore(AbstractStorePro):
    """Pro 版 Excel 存储，复用 ExcelStoreBase 单例并扩展 homefeed/trending sheet"""

    def __init__(self, platform: str, crawler_type: str = "search", **kwargs):
        self.platform = platform
        self._crawler_type = crawler_type
        self._excel = ExcelStoreBase.get_instance(platform, crawler_type)
        self._homefeed_headers_written = False
        self._trending_headers_written = False

    @property
    def _homefeed_sheet(self):
        """懒加载 HomeFeed sheet"""
        name = "HomeFeed"
        for sheet_name in self._excel.workbook.sheetnames:
            if sheet_name == name:
                return self._excel.workbook[name]
        return self._excel.workbook.create_sheet(name)

    @property
    def _trending_sheet(self):
        """懒加载 Trending sheet"""
        name = "Trending"
        for sheet_name in self._excel.workbook.sheetnames:
            if sheet_name == name:
                return self._excel.workbook[name]
        return self._excel.workbook.create_sheet(name)

    async def store_content(self, content_item: Dict) -> None:
        if content_item:
            await self._excel.store_content(content_item)

    async def store_comment(self, comment_item: Dict) -> None:
        if comment_item:
            await self._excel.store_comment(comment_item)

    async def store_creator(self, creator_item: Dict) -> None:
        if creator_item:
            await self._excel.store_creator(creator_item)

    async def store_homefeed(self, item: Dict) -> None:
        if not item:
            return
        sheet = self._homefeed_sheet
        headers = list(item.keys())
        if not self._homefeed_headers_written:
            self._excel._write_headers(sheet, headers)
            self._homefeed_headers_written = True
        self._excel._write_row(sheet, item, headers)

    async def store_trending(self, item: Dict) -> None:
        if not item:
            return
        sheet = self._trending_sheet
        headers = list(item.keys())
        if not self._trending_headers_written:
            self._excel._write_headers(sheet, headers)
            self._trending_headers_written = True
        self._excel._write_row(sheet, item, headers)

    async def flush(self) -> None:
        await self._excel.flush()

    async def close(self) -> None:
        pass
