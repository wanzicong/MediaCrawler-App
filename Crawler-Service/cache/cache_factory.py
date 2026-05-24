# -*- coding: utf-8 -*-
import config
from cache.abs_cache import AbstractCache


class CacheFactory:
    """Cache factory, create cache client by cache type"""

    @staticmethod
    def create_cache(cache_type: str) -> AbstractCache:
        if cache_type == config.CACHE_TYPE_REDIS:
            from cache.redis_cache import RedisCache
            return RedisCache(
                host=config.REDIS_DB_HOST,
                port=config.REDIS_DB_PORT,
                password=config.REDIS_DB_PWD,
                db=config.REDIS_DB_NUM,
            )
        elif cache_type == config.CACHE_TYPE_MEMORY:
            from cache.local_cache import ExpiringLocalCache
            return ExpiringLocalCache()
        else:
            raise ValueError(f"Unsupported cache type: {cache_type}")
