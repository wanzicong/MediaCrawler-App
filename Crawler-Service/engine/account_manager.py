# -*- coding: utf-8 -*-
"""
多账号 + IP代理池管理器

功能：
- 多账号轮询调度 (RoundRobin / LeastUsed / 冷却机制)
- 账号-IP 绑定，模拟真实用户
- 账号状态监控 (活跃/冷却/封禁)
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx

DATA_API_URL = os.getenv("DATA_API_URL", "http://127.0.0.1:8080")


class AccountStatus(str, Enum):
    ACTIVE = "active"
    COOLING = "cooling"
    BANNED = "banned"
    RATE_LIMITED = "rate_limited"


class ScheduleStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"
    RANDOM = "random"


@dataclass
class Account:
    """平台账号"""
    id: int
    platform: str
    username: str = ""
    phone: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    user_agent: str = ""

    request_count: int = 0
    daily_request_count: int = 0
    last_used: float = 0.0

    status: AccountStatus = AccountStatus.ACTIVE
    cooldown_until: float = 0.0

    max_daily_requests: int = 500
    cooldown_seconds: int = 600

    def is_available(self) -> bool:
        now = time.time()
        if self.status == AccountStatus.BANNED:
            return False
        if self.status == AccountStatus.RATE_LIMITED:
            return False
        if self.status == AccountStatus.COOLING and now < self.cooldown_until:
            return False
        if self.daily_request_count >= self.max_daily_requests:
            return False
        return True

    def mark_used(self, count: int = 1) -> None:
        self.request_count += count
        self.daily_request_count += count
        self.last_used = time.time()

    def enter_cooldown(self, seconds: int = 0) -> None:
        seconds = seconds or self.cooldown_seconds
        self.status = AccountStatus.COOLING
        self.cooldown_until = time.time() + seconds

    def reset_daily(self) -> None:
        self.daily_request_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "platform": self.platform,
            "username": self.username, "status": self.status.value,
            "daily_requests": self.daily_request_count,
        }


@dataclass
class ProxyBinding:
    account_id: int
    proxy: Dict[str, Any]
    bound_at: float = 0.0


class AccountManager:
    """
    多账号 + IP代理池管理器

    manager = AccountManager("xhs")
    await manager.load_accounts()
    account, proxy = await manager.acquire()
    try:
        # 爬取...
        manager.mark_success()
    except RateLimitError:
        manager.mark_rate_limited()
    finally:
        await manager.release()
    """

    def __init__(
        self,
        platform: str,
        strategy: ScheduleStrategy = ScheduleStrategy.LEAST_USED,
        enable_ip_proxy: bool = False,
        ip_proxy_pool_count: int = 2,
    ):
        self.platform = platform
        self.strategy = strategy
        self.enable_ip_proxy = enable_ip_proxy
        self.ip_proxy_pool_count = ip_proxy_pool_count

        self._accounts: List[Account] = []
        self._current_index = 0
        self._lock = asyncio.Lock()

        self._proxy_pool: Any = None
        self._current_account: Optional[Account] = None
        self._current_proxy: Optional[Dict] = None
        self._bindings: Dict[int, ProxyBinding] = {}

    async def load_accounts(self) -> int:
        """从 Data-API 加载平台账号列表"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{DATA_API_URL}/api/internal/accounts",
                    params={"platform": self.platform, "status": "active"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._accounts = [
                        Account(
                            id=item["id"], platform=item.get("platform", self.platform),
                            username=item.get("username", ""),
                            phone=item.get("phone", ""),
                            cookies=item.get("cookies", {}),
                            user_agent=item.get("user_agent", ""),
                        )
                        for item in data.get("accounts", [])
                    ]
                    print(f"[AccountManager] 加载 {len(self._accounts)} 个 {self.platform} 账号")
        except Exception as e:
            print(f"[AccountManager] 加载账号失败: {e}")

        if not self._accounts:
            self._accounts = [Account(id=0, platform=self.platform, username="default")]
        return len(self._accounts)

    async def acquire(self) -> Tuple[Optional[Account], Optional[Dict]]:
        """获取一个可用账号和可选代理"""
        async with self._lock:
            account = self._select_account()
            if account is None:
                raise NoAvailableAccountError(f"没有可用的 {self.platform} 账号")

            proxy = None
            if self.enable_ip_proxy:
                proxy = await self._get_proxy(account.id)

            account.mark_used()
            self._current_account = account
            self._current_proxy = proxy

            msg = f"[AccountManager] 分配账号: {account.username} #{account.id}"
            if proxy:
                msg += f" 代理: {proxy.get('ip', '')}"
            print(msg)
            return account, proxy

    async def release(self) -> None:
        async with self._lock:
            self._current_account = None
            self._current_proxy = None

    def mark_success(self) -> None:
        pass

    def mark_rate_limited(self, cooldown_seconds: int = 0) -> None:
        if self._current_account:
            seconds = cooldown_seconds or self._current_account.cooldown_seconds
            self._current_account.enter_cooldown(seconds)
            print(f"[AccountManager] {self._current_account.username} 限流冷却 {seconds}s")

    def mark_banned(self) -> None:
        if self._current_account:
            self._current_account.status = AccountStatus.BANNED
            print(f"[AccountManager] {self._current_account.username} 已标记封禁")

    def get_current_proxy_config(self) -> Optional[Dict]:
        if not self._current_proxy:
            return None
        p = self._current_proxy
        config: Dict[str, Any] = {"server": f"http://{p['ip']}:{p['port']}"}
        if p.get("user") and p.get("password"):
            config["username"] = p["user"]
            config["password"] = p["password"]
        return config

    def get_current_cookies(self) -> Dict[str, str]:
        return dict(self._current_account.cookies) if self._current_account else {}

    def get_current_user_agent(self) -> str:
        return self._current_account.user_agent if self._current_account else ""

    def get_status(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "total_accounts": len(self._accounts),
            "available": sum(1 for a in self._accounts if a.is_available()),
            "accounts": [a.to_dict() for a in self._accounts],
            "current": self._current_account.to_dict() if self._current_account else None,
        }

    def _select_account(self) -> Optional[Account]:
        available = [a for a in self._accounts if a.is_available()]
        if not available:
            return None
        if self.strategy == ScheduleStrategy.ROUND_ROBIN:
            self._current_index = (self._current_index + 1) % len(available)
            return available[self._current_index]
        elif self.strategy == ScheduleStrategy.LEAST_USED:
            return min(available, key=lambda a: a.daily_request_count)
        elif self.strategy == ScheduleStrategy.RANDOM:
            return random.choice(available)
        return available[0]

    async def _get_proxy(self, account_id: int) -> Optional[Dict]:
        if self._proxy_pool is None:
            await self._init_proxy_pool()
        if self._proxy_pool is None:
            return None
        try:
            ip_model = await self._proxy_pool.get_or_refresh_proxy()
            proxy = {
                "ip": ip_model.ip, "port": ip_model.port,
                "user": ip_model.user, "password": ip_model.password,
            }
            self._bindings[account_id] = ProxyBinding(account_id=account_id, proxy=proxy, bound_at=time.time())
            return proxy
        except Exception as e:
            print(f"[AccountManager] 获取代理失败: {e}")
            return None

    async def _init_proxy_pool(self) -> None:
        try:
            import config as _cfg
            from proxy.proxy_ip_pool import create_ip_pool
            self._proxy_pool = await create_ip_pool(
                ip_pool_count=self.ip_proxy_pool_count, enable_validate_ip=True,
            )
            print(f"[AccountManager] IP代理池初始化完成")
        except Exception as e:
            print(f"[AccountManager] IP代理池初始化失败: {e}")


class NoAvailableAccountError(Exception):
    pass

