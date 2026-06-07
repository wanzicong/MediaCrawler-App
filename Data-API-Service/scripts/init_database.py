# -*- coding: utf-8 -*-
"""初始化数据库：建库、建表、补齐列、种子默认方案"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保 Data-API-Service 根目录在 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from database.db_session import create_tables  # noqa: E402
from scripts.sync_schema import sync_schema  # noqa: E402
from services.config_service import ConfigService  # noqa: E402


async def init_database() -> None:
    await create_tables("db")
    patches = await sync_schema()
    await ConfigService.ensure_default_profile()
    print("✓ 数据库初始化完成")
    if patches:
        print(f"  已补齐列: {', '.join(patches)}")


def main() -> None:
    asyncio.run(init_database())


if __name__ == "__main__":
    main()
