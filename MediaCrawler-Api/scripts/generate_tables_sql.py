# -*- coding: utf-8 -*-
"""从 SQLAlchemy 模型导出 MySQL DDL 到项目根目录 sql/01_tables.sql"""

from pathlib import Path

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from database.models import Base
import database.system_models  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sql" / "01_tables.sql"

tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
parts = [
    "-- 由 MediaCrawler-Api/scripts/generate_tables_sql.py 生成",
    "-- 执行: pnpm db:generate-sql",
    "USE `media_crawler`;",
    "",
]
for table in tables:
    ddl = str(CreateTable(table).compile(dialect=mysql.dialect())).strip()
    parts.append(ddl + ";")
    parts.append("")

OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {len(tables)} tables -> {OUT}")
