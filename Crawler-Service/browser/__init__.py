# -*- coding: utf-8 -*-
"""
浏览器抽象层 - 解耦 Playwright 依赖
"""

from .base import AbstractBrowser, BrowserContext, BrowserPage, BrowserLaunchOptions
from .playwright_impl import PlaywrightBrowser

__all__ = [
    "AbstractBrowser",
    "BrowserContext",
    "BrowserPage",
    "BrowserLaunchOptions",
    "PlaywrightBrowser",
]

