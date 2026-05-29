# -*- coding: utf-8 -*-
"""
HomeFeed + 热搜榜单爬虫抽象

新增爬取类型: homefeed (首页推荐流), trending (热搜榜单)
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional


class HomeFeedMixin:
    """首页推荐流爬取混入类"""

    homefeed_url: str = ""
    homefeed_referer: str = ""

    @abstractmethod
    async def crawl_homefeed(self) -> List[Dict[str, Any]]:
        """
        爬取首页推荐流内容

        Returns:
            feed_items: 推荐流内容列表
        """
        ...

    @abstractmethod
    async def parse_homefeed_item(self, raw_item: Any) -> Dict[str, Any]:
        """
        解析单个推荐流项目

        Args:
            raw_item: 原始数据 (API响应/json/HTML元素)

        Returns:
            dict: 标准化的内容项
        """
        ...

    @abstractmethod
    async def scroll_homefeed(self, scroll_count: int = 3) -> None:
        """
        模拟滚动加载更多推荐内容

        Args:
            scroll_count: 滚动次数
        """
        ...


class TrendingMixin:
    """热搜榜单爬取混入类"""

    trending_url: str = ""
    trending_referer: str = ""

    @abstractmethod
    async def crawl_trending(self, board_type: str = "hot") -> List[Dict[str, Any]]:
        """
        爬取热搜榜单

        Args:
            board_type: 榜单类型 (hot/search/rising/video/entertainment)

        Returns:
            trending_items: 热搜内容列表，包含 rank, title, hot_value, url 等
        """
        ...

    @abstractmethod
    async def get_trending_boards(self) -> List[Dict[str, str]]:
        """
        获取可用榜单列表

        Returns:
            [{"id": "hot", "name": "热搜榜"}, {"id": "rising", "name": "上升榜"}, ...]
        """
        ...


# 标准化的 HomeFeed 数据结构
HOME_FEED_SCHEMA = {
    "note_id": "",         # 帖子/视频 ID
    "title": "",           # 标题
    "desc": "",            # 描述
    "author": {            # 作者信息
        "id": "",
        "name": "",
        "avatar": "",
    },
    "type": "note",        # note | video | article
    "cover": "",           # 封面图 URL
    "url": "",             # 详情页 URL
    "like_count": 0,
    "comment_count": 0,
    "share_count": 0,
    "tags": [],            # 标签
    "publish_time": 0,     # 发布时间戳
    "recommend_reason": "",# 推荐理由
}

# 标准化的 Trending 数据结构
TRENDING_SCHEMA = {
    "rank": 0,             # 排名
    "title": "",           # 热搜词/标题
    "hot_value": 0,        # 热度值
    "url": "",             # 链接
    "label": "",           # 标签 (新/热/爆)
    "board_type": "hot",   # 榜单类型
    "platform": "",        # 平台
    "fetch_time": 0,       # 采集时间戳
    "is_ad": False,        # 是否广告
}
