# -*- coding: utf-8 -*-
import redis

from cache.abs_cache import AbstractCache


class RedisCache(AbstractCache):

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, password: str = "", db: int = 0):
        self._redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
        )

    def get(self, key: str):
        return self._redis_client.get(key)

    def set(self, key: str, value: str, ex: int):
        self._redis_client.set(key, value, ex=ex)

    def keys(self, pattern: str):
        return self._redis_client.keys(pattern)
