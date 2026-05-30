# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 项目概述

MediaCrawler 是一个多平台自媒体数据采集工具，支持小红书、抖音、快手、B站、微博、贴吧、知乎。基于 Playwright 浏览器自动化，通过 CDP 协议控制真实浏览器实现反检测。项目是 pnpm monorepo，包含 Python 后端（两个服务）和 React 前端。

## 常用命令

### 基础设施

```bash
pnpm db:up          # 启动 MySQL Docker 容器 + 同步 .env
pnpm db:down        # 停止 MySQL
pnpm db:reset       # 清空数据卷并重新初始化数据库
pnpm db:status      # 查看 MySQL 容器状态
pnpm db:sync-env    # 同步数据库配置到各服务 .env 文件
```

MySQL: root / 123456, 数据库 media_crawler, 端口 3306

### 开发

```bash
# 数据 API 服务 (FastAPI, 端口 8080) — 数据库、配置、AI、关键词管理
pnpm dev:data-api   # 启动 Data-API-Service

# 爬虫服务 (FastAPI, 端口 8081) — 爬虫控制、WebSocket 日志推送
pnpm dev:crawler    # 启动 Crawler-Service

# 同时启动两个后端服务
pnpm dev:api        # 并行启动 data-api + crawler

# 前端开发服务器 (Vite, 端口 5173)
pnpm dev:web        # 启动前端 dev server

# 全部并行启动
pnpm dev            # 并行启动 data-api + crawler + web

# 爬虫命令行模式 (非 WebUI)
cd Crawler-Service && uv run python main.py --help
cd Crawler-Service && uv run python main.py --platform xhs --keywords "关键词" --crawler-type search
cd Crawler-Service && uv run python main.py --task-id <id>

# 安装 Python 依赖
pnpm install:api    # 即 cd Data-API-Service && uv sync && cd ../Crawler-Service && uv sync
```

### 构建与检查

```bash
pnpm build          # 构建前端到 MediaCrawler-Web/dist/
pnpm lint:web       # ESLint 检查前端代码
pnpm build:web      # TypeScript 编译 + Vite 构建
```

### 测试

```bash
cd Crawler-Service && uv run pytest tests/ -v
cd Crawler-Service && uv run python -m pytest tests/test_store_factory.py -v
```

## 架构

### 服务拆分

项目已从单体 `MediaCrawler-Api/` 重构为两个独立服务，通过 HTTP 通信（零代码共享）：

| 服务 | 端口 | 职责 |
|------|------|------|
| **Data-API-Service** | 8080 | 数据库 CRUD、配置方案管理、关键词管理、AI 对话/评论分析、平台元数据、内部 API |
| **Crawler-Service** | 8081 | 爬虫子进程管理、WebSocket 实时日志推送、爬虫控制 API、浏览器自动化引擎 |

### 整体结构

```
MediaCrawler-App/
├── Data-API-Service/           # 数据 & 配置中心 (FastAPI, 端口 8080)
│   ├── api/
│   │   ├── main.py             # FastAPI app (v2.0.0), 注册 8 个 router
│   │   ├── routers/            # data, data_db, ai, keywords, config_mgmt, platforms, system, internal
│   │   └── schemas/            # Pydantic 模型 (CrawlerPayloadSchema, Profile, Task)
│   ├── database/
│   │   ├── models.py           # 24 个平台业务表 ORM 模型 (共用 Base)
│   │   ├── system_models.py    # 6 个系统表 (CrawlerProfile, CrawlerTask, ChatSession, ChatMemory, Keyword, Platform)
│   │   └── db_session.py       # 异步引擎管理 (MySQL/SQLite/Postgres), 自动建库建表
│   ├── services/
│   │   ├── config_service.py   # 方案/任务 CRUD, payload 合并
│   │   ├── data_query_service.py # 分页查询平台数据, PLATFORM_META 缓存
│   │   └── platform_service.py # 平台元数据管理, 种子数据
│   └── config/db_config.py     # 数据库连接配置 (读取环境变量)
│
├── Crawler-Service/            # 爬虫引擎 (FastAPI, 端口 8081)
│   ├── main.py                 # CLI 爬虫入口 + CrawlerFactory (子进程模式)
│   ├── var.py                  # ContextVar 上下文变量 (request_keyword, crawler_type, comment_tasks)
│   ├── api/
│   │   ├── main.py             # FastAPI app (v2.0.0), crawler + websocket router
│   │   ├── routers/
│   │   │   ├── crawler.py      # 爬虫控制 (start/stop/status/rerun/cleanup-zombies)
│   │   │   └── websocket.py    # WebSocket 实时日志 + 状态推送
│   │   ├── schemas/            # 请求/响应 Pydantic 模型
│   │   └── services/
│   │       └── crawler_manager.py  # 子进程管理器 (单例), 日志队列, 任务排队
│   ├── base/base_crawler.py    # 抽象基类 (AbstractCrawler, AbstractLogin, AbstractStore)
│   ├── media_platform/         # 各平台爬虫实现 (xhs/dy/ks/bili/wb/tieba/zhihu)
│   ├── config/
│   │   ├── base_config.py      # 全局配置 (module-level 变量)
│   │   ├── applier.py          # apply_crawler_payload() — 运行时配置注入
│   │   └── platform_risk_profiles.py  # 平台风控等级
│   ├── model/                  # 平台数据模型 (URL 解析, 请求构造)
│   ├── constant/               # 平台 URL 常量
│   ├── store/                  # 数据存储层 (各平台 + Excel/CSV/JSON)
│   ├── services/               # 子进程内服务 (task_loader, progress_reporter)
│   ├── tools/                  # 工具 (CDP 浏览器, 文件写入, 滑块验证等)
│   ├── cache/                  # 缓存层 (本地/Redis)
│   └── proxy/                  # 代理模块
│
├── MediaCrawler-Web/           # React 前端 (Vite, 端口 5173)
│   └── src/
│       ├── pages/              # Dashboard, Crawler, Data, Settings
│       ├── api/                # axios API 调用层
│       ├── hooks/              # useCrawlerStatus, useCrawlerLogs (WebSocket)
│       ├── stores/             # zustand 状态管理
│       └── router/             # react-router-dom 路由
├── scripts/mysql-manager.mjs   # MySQL Docker 管理脚本
├── sql/                        # 数据库初始化 SQL
└── docker-compose.yml          # MySQL 8.0 容器
```

### Vite 代理路由

前端开发服务器根据路径前缀将请求分发到不同后端：

```
/api/crawler  → Crawler-Service (8081)    # 爬虫控制
/api/ws       → Crawler-Service (8081)    # WebSocket
/api          → Data-API-Service (8080)   # 数据/AI/配置/关键词
```

### 核心数据流 (WebUI 启动爬虫)

```
前端 Crawler 页面
  → POST /api/crawler/start (payload, 可能含 profile_id)
  → Crawler-Service: crawler_manager.start()
     → 调用 Data-API: POST /api/internal/tasks → 创建任务记录 (status=pending)
     → subprocess: uv run python main.py --task-id <id>  (Crawler-Service 目录下)
        → task_loader: GET /api/internal/tasks/{id} → 获取任务配置
        → config/applier.py: apply_crawler_payload() → 写入 config 模块
        → progress_reporter: PUT /api/internal/tasks/{id}/progress (每 5 秒)
        → CrawlerFactory.create_crawler(platform) → crawler.start()
           → login → search/detail/creator → store_content/store_comment
        → finally: PUT /api/internal/tasks/{id}/finish → 标记完成/失败
     → 子进程 stdout 被 CrawlerManager._read_output() 逐行捕获
     → 通过 asyncio.Queue → WebSocket /ws/logs 广播到前端
  → 进程退出时 CrawlerManager 自动 dequeue 下一个排队任务
```

### 服务间通信

Crawler-Service **全部通过 HTTP** 调用 Data-API-Service（`DATA_API_URL` 环境变量，默认 `http://127.0.0.1:8080`），两端零代码共享。内部 API 端点（`/api/internal/*`）：

| 调用方 | 端点 | 用途 |
|--------|------|------|
| crawler_manager | `POST /api/internal/tasks` | 创建任务记录 |
| crawler_manager | `GET /api/internal/profiles/{id}` | 获取方案配置 |
| crawler_manager | `PUT /api/internal/tasks/{id}/finish` | 标记任务完成/失败 |
| crawler router | `GET/DELETE /api/internal/tasks[/{id}]` | 查询/删除任务 |
| task_loader (子进程) | `GET /api/internal/tasks/{id}` | 加载任务配置 |
| progress_reporter (子进程) | `PUT /api/internal/tasks/{id}/progress` | 上报进度 |
| main.py (子进程 finally) | `PUT /api/internal/tasks/{id}/finish` | 最终状态更新 |
| 爬虫 store 层 | `POST /api/internal/data/batch` | 批量写入爬取数据 |

### 关键设计决策

1. **配置系统**: `Crawler-Service/config/` 使用 Python module-level 变量而非 class。通过 `apply_crawler_payload()` 动态覆写。多进程场景下通过 `--task-id` 从 Data-API-Service 加载配置而非命令行参数传递。Data-API-Service 的 `config/` 只管理数据库连接配置。

2. **任务调度**: `CrawlerManager` 是单例，同一时间只运行一个爬虫子进程。新任务在运行时自动排队（`_task_queue`），前一个完成后自动出队执行。使用 `asyncio.Lock` 防止竞态条件。

3. **数据库**: 所有 ORM 模型在 Data-API-Service 的 `database/` 中定义，系统表和业务表共用同一个 SQLAlchemy `Base`。Crawler-Service 不直接操作数据库，爬取数据通过 `POST /api/internal/data/batch` 写入。

4. **CDP 浏览器模式**: 默认启用 CDP 模式 (`ENABLE_CDP_MODE = True`)，通过 Chrome DevTools Protocol 控制用户本地 Chrome/Edge 实现反检测。高风险平台（小红书、抖音等）强制 CDP。每个平台有风控等级配置（`platform_risk_profiles.py`）。

5. **前端 WebSocket**: 实时日志和状态通过两个 WebSocket 端点推送 (`/ws/logs`, `/ws/status`)，由 Crawler-Service 的 `ConnectionManager` 广播。日志保留最近 500 条。

6. **子进程日志解析**: 爬虫子进程 stdout 被逐行捕获，`CrawlerManager` 根据消息内容自动识别日志级别（error/warning/success/debug/info）并推送到 WebSocket。

### 平台爬虫模式

每个 `media_platform/<name>/` 目录包含该平台爬虫实现，继承 `base/base_crawler.py` 中的抽象基类：
- `AbstractCrawler` — `start()`, `search()`, `launch_browser()`
- `AbstractLogin` — `begin()`, `login_by_qrcode()`, `login_by_mobile()`, `login_by_cookies()`
- `AbstractStore` — `store_content()`, `store_comment()`, `store_creator()`

爬取类型由 `CRAWLER_TYPE` 决定：`search`（关键词搜索）、`detail`（指定帖子ID）、`creator`（创作者主页）。

### 子进程优雅关闭

`tools/app_runner.py` 处理信号：首次 SIGINT/SIGTERM 触发 graceful shutdown（关闭浏览器、停止进度上报），再次收到信号调用 `os._exit(130)` 强制退出。`CrawlerManager` 停止任务时先 SIGTERM，15 秒后 SIGKILL。
