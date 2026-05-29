# -*- coding: utf-8 -*-
"""
平台风控限流器 — 令牌桶算法

每个平台独立桶，控制请求频率，避免触发平台反爬。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class _Bucket:
    rate: float          # 令牌生成速率 (tokens/sec)
    max_tokens: float    # 桶容量 (最大突发)
    tokens: float        # 当前令牌数
    last_refill: float   # 上次填充时间


_PLATFORM_CONFIG: Dict[str, tuple] = {
    "xhs":   (10.0, 15.0),   # 小红书 10/min, burst 15
    "dy":    (20.0, 30.0),   # 抖音 20/min
    "ks":    (15.0, 20.0),   # 快手
    "bili":  (30.0, 40.0),   # B站
    "wb":    (15.0, 20.0),   # 微博
    "tieba": (15.0, 20.0),   # 贴吧
    "zhihu": (15.0, 20.0),   # 知乎
}


class RateLimiter:
    """平台级别令牌桶限流器"""

    def __init__(self):
        self._buckets: Dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        for platform in _PLATFORM_CONFIG:
            rate, max_tokens = _PLATFORM_CONFIG[platform]
            self._buckets[platform] = _Bucket(
                rate=rate / 60.0,  # 转换为 tokens/sec
                max_tokens=max_tokens,
                tokens=max_tokens,
                last_refill=time.monotonic(),
            )
            self._semaphores[platform] = asyncio.Semaphore(2)

    def _refill(self, bucket: _Bucket) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(bucket.max_tokens, bucket.tokens + elapsed * bucket.rate)
        bucket.last_refill = now

    async def acquire(self, platform: str, tokens: float = 1.0) -> float:
        """获取令牌，返回等待时间。0 = 立即可用。"""
        bucket = self._buckets.get(platform)
        if bucket is None:
            return 0.0

        async with self._lock:
            self._refill(bucket)
            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return 0.0

        # 令牌不足，计算等待时间
        deficit = tokens - bucket.tokens
        wait = deficit / bucket.rate

        await asyncio.sleep(wait)

        async with self._lock:
            self._refill(bucket)
            bucket.tokens -= tokens
            return wait

    async def acquire_slot(self, platform: str) -> None:
        """获取并发槽位（同一平台同时最多 2 个任务）"""
        sem = self._semaphores.get(platform)
        if sem:
            await sem.acquire()

    def release_slot(self, platform: str) -> None:
        sem = self._semaphores.get(platform)
        if sem:
            sem.release()

    def get_status(self) -> Dict[str, dict]:
        """获取各平台限流状态"""
        result = {}
        for platform, bucket in self._buckets.items():
            self._refill(bucket)
            sem = self._semaphores.get(platform)
            result[platform] = {
                "rate_per_min": int(bucket.rate * 60),
                "available": round(bucket.tokens, 1),
                "max_burst": int(bucket.max_tokens),
                "used_slots": 2 - (sem._value if sem else 2),
                "max_slots": 2,
            }
        return result


# 全局实例
rate_limiter = RateLimiter()
