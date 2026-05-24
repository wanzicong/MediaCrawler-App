# -*- coding: utf-8 -*-
import threading
import time

from cache.abs_cache import AbstractCache


class ExpiringLocalCache(AbstractCache):

    def __init__(self, cron_interval: int = 10):
        self._store: dict = {}
        self._lock = threading.Lock()
        self._cron_interval = cron_interval
        self._stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        while not self._stop_event.wait(self._cron_interval):
            self._remove_expired()

    def _remove_expired(self):
        now = time.time()
        with self._lock:
            expired_keys = [k for k, (_, exp) in self._store.items() if now >= exp]
            for k in expired_keys:
                del self._store[k]

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, exp = entry
            if time.time() >= exp:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: str, ex: int):
        with self._lock:
            self._store[key] = (value, time.time() + ex)

    def keys(self, pattern: str):
        import fnmatch
        with self._lock:
            return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def __del__(self):
        self._stop_event.set()
