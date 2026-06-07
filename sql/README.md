# 数据库初始化说明

Docker 首次启动时仅执行 `00_init.sql`（创建 `media_crawler` 库）。

**表结构由 ORM 管理**，请在 MySQL 就绪后执行：

```bash
pnpm db:init
```

或在 `pnpm db:up` / `pnpm db:reset` 时自动执行。

历史 SQL 快照见 `legacy/` 目录（仅供参考，不再用于自动初始化）。
