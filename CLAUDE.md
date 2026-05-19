# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

MediaCrawler 是一个多平台自媒体数据采集工具，支持小红书、抖音、快手、B站、微博、贴吧、知乎。基于 Playwright 浏览器自动化，通过 CDP 协议控制真实浏览器实现反检测。项目是 pnpm monorepo，包含 Python 后端和 React 前端。

## 常用命令

### 基础设施

```bash
pnpm db:up          # 启动 MySQL Docker 容器 + 同步 .env
pnpm db:down        # 停止 MySQL
pnpm db:reset       # 清空数据卷并重新初始化数据库
pnpm db:status      # 查看 MySQL 容器状态
pnpm db:sync-env    # 同步数据库配置到 MediaCrawler-Api/.env
```

MySQL: root / 123456, 数据库 media_crawler, 端口 3306

### 开发

```bash
# 后端 API 服务 (FastAPI, 端口 8080)
pnpm dev:api        # 启动 API 服务 (uvicorn --reload)

# 前端开发服务器 (Vite, 端口 5173, 自动代理 /api 到 8080)
pnpm dev:web        # 启动前端 dev server

# 同时启动前后端
pnpm dev            # 并行启动 api + web

# 爬虫命令行模式 (非 WebUI)
cd MediaCrawler-Api && uv run python main.py --help
cd MediaCrawler-Api && uv run python main.py --platform xhs --keywords "关键词" --crawler-type search

# 安装 Python 依赖
pnpm install:api    # 即 cd MediaCrawler-Api && uv sync
```

### 构建与检查

```bash
pnpm build          # 构建前端到 MediaCrawler-Web/dist/
pnpm lint:web       # ESLint 检查前端代码
pnpm build:web      # TypeScript 编译 + Vite 构建
```

构建后前端静态文件输出到 `MediaCrawler-Web/dist/`，后端 API 服务器会直接 serve 这些文件。

### 测试

```bash
cd MediaCrawler-Api && uv run pytest tests/ -v
cd MediaCrawler-Api && uv run python -m pytest tests/test_store_factory.py -v
```

## 架构

### 整体结构

```
MediaCrawler-App/
├── MediaCrawler-Api/       # Python 后端 (FastAPI + 爬虫引擎)
│   ├── main.py             # CLI 爬虫入口 + CrawlerFactory
│   ├── api/                # WebUI API 层
│   │   ├── main.py         # FastAPI app 定义, 路由注册, 静态文件 serve
│   │   ├── routers/        # REST API (crawler, config_mgmt, data, data_db, system, websocket)
│   │   ├── services/       # crawler_manager.py — 子进程管理器 (单例)
│   │   └── schemas/        # Pydantic 请求/响应模型
│   ├── base/               # 抽象基类 (AbstractCrawler, AbstractLogin, AbstractStore)
│   ├── media_platform/     # 各平台爬虫实现 (xhs/dy/ks/bili/wb/tieba/zhihu)
│   ├── config/             # 全局配置模块 (Python module-level, 不是 class)
│   │   ├── base_config.py  # 所有配置常量, 平台特定配置导入
│   │   ├── applier.py      # apply_crawler_payload() — 将字典写入 config 模块
│   │   └── platform_risk_profiles.py  # 平台风控等级配置
│   ├── database/           # SQLAlchemy ORM
│   │   ├── models.py       # 业务表模型 (各平台内容/评论表, 共用 Base)
│   │   ├── system_models.py # 系统表 (CrawlerProfile, CrawlerTask, 也共用 Base)
│   │   └── db_session.py   # 异步引擎管理, 自动建库建表
│   ├── services/           # 后端服务层
│   │   ├── config_service.py   # ConfigService — 方案/任务 CRUD (MySQL)
│   │   ├── progress_reporter.py # 子进程进度上报
│   │   └── task_loader.py      # 子进程从 MySQL 加载任务配置
│   ├── store/              # 数据存储层 (各平台 + Excel)
│   ├── tools/              # 工具 (CDP 浏览器、文件写入、滑块验证等)
│   └── tests/              # pytest 测试
├── MediaCrawler-Web/       # React 前端
│   └── src/
│       ├── pages/          # Dashboard, Crawler, Data, Settings
│       ├── api/            # axios API 调用层
│       ├── hooks/          # useCrawlerStatus, useCrawlerLogs (WebSocket)
│       ├── stores/         # zustand 状态管理
│       └── router/         # react-router-dom 路由定义
├── scripts/mysql-manager.mjs  # MySQL Docker 管理脚本
├── sql/                    # 数据库初始化 SQL 脚本
└── docker-compose.yml      # MySQL 8.0 容器定义
```

### 核心数据流 (WebUI 启动爬虫)

```
前端 Crawler 页面
  → POST /api/crawler/start (payload)
  → crawler_manager.start()
  → ConfigService.create_task() → 写入 crawler_task 表 (status=pending)
  → subprocess: uv run python main.py --task-id <id>
  → task_loader 从 MySQL 加载配置 → apply_crawler_payload() → 写入 config 模块
  → CrawlerFactory.create_crawler(platform) → crawler.start()
  → 子进程 stdout 被 CrawlerManager._read_output() 逐行捕获
  → 通过 asyncio.Queue → WebSocket /ws/logs 广播到前端
  → progress_reporter 定期更新 crawler_task.progress 字段
  → 进程退出时 ConfigService.mark_task_finished() 更新状态
```

### 关键设计决策

1. **配置系统**: `config/` 目录下的模块使用 Python module-level 变量而非 class。通过 `apply_crawler_payload()` 动态覆写。这意味着 `import config` 后直接 `config.PLATFORM` 访问，是多进程场景下通过 `--task-id` 从 DB 加载配置而非命令行参数传递。

2. **任务调度**: `CrawlerManager` 是单例，同一时间只运行一个爬虫子进程。新任务在运行时自动排队（`_task_queue`），前一个完成后自动出队执行。

3. **数据库**: 系统表（crawler_profile, crawler_task）和业务数据表都走 MySQL，共用同一个 SQLAlchemy `Base`。`get_mysql_session()` 强制走 MySQL 无论 `SAVE_DATA_OPTION` 设什么值。

4. **CDP 浏览器模式**: 默认启用 CDP 模式 (`ENABLE_CDP_MODE = True`)，通过 Chrome DevTools Protocol 控制用户本地 Chrome/Edge，利用真实浏览器环境反检测。每个平台有风控等级配置（`platform_risk_profiles.py`），高风险平台强制 CDP。

5. **前端 WebSocket**: 实时日志和状态通过两个 WebSocket 端点推送 (`/ws/logs`, `/ws/status`)，后端使用 `ConnectionManager` 广播。

### 平台爬虫模式

每个 `media_platform/<name>/` 目录包含该平台的爬虫实现，继承 `base/base_crawler.py` 中的抽象基类：
- `AbstractCrawler` — `start()`, `search()`, `launch_browser()`
- `AbstractLogin` — `begin()`, `login_by_qrcode()`, `login_by_mobile()`, `login_by_cookies()`
- `AbstractStore` — `store_content()`, `store_comment()`, `store_creator()`

爬取类型由 `CRAWLER_TYPE` 决定：`search`（关键词搜索）、`detail`（指定帖子ID）、`creator`（创作者主页）。
