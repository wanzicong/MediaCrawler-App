# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod


class AbstractCache(ABC):

    @abstractmethod
    def get(self, key: str):
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: str, ex: int):
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: str):
        raise NotImplementedError
