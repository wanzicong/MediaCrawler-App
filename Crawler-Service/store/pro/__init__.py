# -*- coding: utf-8 -*-
"""
Pro 版本多存储后端

统一存储接口，支持:
- HTTP -> Data-API -> MySQL
- CSV 文件
- Excel 文件
- JSON/JSONL 文件
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AbstractStorePro(ABC):
    """Pro 版本存储抽象 (兼容原 AbstractStore + 新增方法)"""

    @abstractmethod
    async def store_content(self, content_item: Dict) -> None:
        """存储内容 (帖子/笔记/视频)"""
        ...

    @abstractmethod
    async def store_comment(self, comment_item: Dict) -> None:
        """存储评论"""
        ...

    @abstractmethod
    async def store_creator(self, creator_item: Dict) -> None:
        """存储创作者信息"""
        ...

    @abstractmethod
    async def store_homefeed(self, item: Dict) -> None:
        """[新] 存储首页推荐流内容"""
        ...

    @abstractmethod
    async def store_trending(self, item: Dict) -> None:
        """[新] 存储热搜榜单内容"""
        ...

    @abstractmethod
    async def flush(self) -> None:
        """刷写缓冲"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭存储"""
        ...


class StoreFactory:
    """存储工厂 - 根据 save_option 创建对应的 Store 实例"""

    STORES: Dict[str, type] = {}

    @classmethod
    def register(cls, option: str, store_cls: type) -> None:
        cls.STORES[option] = store_cls

    @classmethod
    def create(cls, platform: str, save_option: str = "db", crawler_type: str = "search", **kwargs) -> AbstractStorePro:
        store_cls = cls.STORES.get(save_option)
        if store_cls is None:
            raise ValueError(
                f"Unsupported save option: {save_option}. Available: {list(cls.STORES)}"
            )
        return store_cls(platform=platform, crawler_type=crawler_type, **kwargs)


def _register_default_stores() -> None:
    """注册内置存储实现"""
    from .db_store import ProHttpStore
    from .csv_store import ProCsvStore
    from .json_store import ProJsonStore, ProJsonlStore
    from .excel_store import ProExcelStore

    StoreFactory.register("db", ProHttpStore)
    StoreFactory.register("csv", ProCsvStore)
    StoreFactory.register("json", ProJsonStore)
    StoreFactory.register("jsonl", ProJsonlStore)
    StoreFactory.register("excel", ProExcelStore)


_register_default_stores()
