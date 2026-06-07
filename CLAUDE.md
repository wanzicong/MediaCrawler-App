# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

MediaCrawler 是一个多平台自媒体数据采集工具，支持小红书、抖音、快手、B站、微博、贴吧、知乎。基于 Playwright 浏览器自动化，通过 CDP 协议控制真实浏览器实现反检测。项目是 pnpm monorepo，包含 4 个 Python 后端服务 + React 前端（端口 10001）。

## 常用命令

### 基础设施

```bash
pnpm db:up          # 启动 MySQL + 同步 .env + ORM 自动建表
pnpm db:down        # 停止 MySQL
pnpm db:reset       # 清空数据卷并通过 ORM 重新初始化
pnpm db:init        # 手动 ORM 建表 + 补齐列 + 种子默认方案
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

# 前端开发服务器 (Vite, 端口 10001)
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

项目已从单体 `MediaCrawler-Api/` 重构为四个独立服务，通过 HTTP 通信（零代码共享）：

| 服务 | 端口 | 职责 |
|------|------|------|
| **Data-API-Service** | 8080 | 数据库 CRUD、配置方案管理、关键词管理、AI 对话/评论分析、平台元数据、内部 API、收藏审阅 |
| **Crawler-Service** | 8081 | 爬虫子进程管理（MAX_CONCURRENT=3）、WebSocket 实时日志推送、Pro 多任务调度、引擎层 |
| **Browser-Service** | 9500 | Chrome/Edge 浏览器实例池管理、CDP 端口分配、健康检查与自动恢复 |
| **Signer-Service** | 8082 | 小红书/抖音 API 请求签名 |

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
├── MediaCrawler-Web/           # React 前端 (Vite, 端口 10001)
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

前端开发服务器根据路径前缀将请求分发到不同后端（目标地址由环境变量控制，`.env.development` 优先级高于 `.env`）：

```env
# MediaCrawler-Web/.env.development（开发时修改此文件）
VITE_API_PROXY_TARGET=http://127.0.0.1:8080      # → Data-API-Service
VITE_CRAWLER_PROXY_TARGET=http://127.0.0.1:8081  # → Crawler-Service
```

```
/api/crawler-pro → Crawler-Service    # Pro 爬虫控制
/api/crawler     → Crawler-Service    # 爬虫控制 + 任务日志代理
/api/ws          → Crawler-Service    # WebSocket
/api             → Data-API-Service   # 数据/AI/配置/关键词
```

⚠️ **重要**：`/api/crawler` 路径代理到 Crawler-Service，Crawler-Service **再通过带 `X-API-Token` 的 HTTP 请求**转调 Data-API 的 `/api/internal/*`。前端**绝不**直接调 `/api/internal/*`。

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
| crawler router | `GET/DELETE /api/internal/tasks[/{id}]` | 查询/删除任务（前端代理） |
| crawler router | `GET /api/internal/tasks/{id}/logs` | 查询任务日志（前端代理） |
| task_loader (子进程) | `GET /api/internal/tasks/{id}` | 加载任务配置 |
| progress_reporter (子进程) | `PUT /api/internal/tasks/{id}/progress` | 上报进度 |
| main.py (子进程 finally) | `PUT /api/internal/tasks/{id}/finish` | 最终状态更新 |
| 爬虫 store 层 | `POST /api/internal/data/batch` | 批量写入爬取数据 |
| crawler_manager | `POST /api/internal/logs/batch` | 批量写入任务日志 |

### 关键设计决策

1. **配置系统**: `Crawler-Service/config/` 使用 Python module-level 变量而非 class。通过 `apply_crawler_payload()` 动态覆写。多进程场景下通过 `--task-id` 从 Data-API-Service 加载配置而非命令行参数传递。Data-API-Service 的 `config/` 只管理数据库连接配置。

2. **任务调度**: `CrawlerManager` 是单例，支持最多 3 个并发爬虫子进程（MAX_CONCURRENT=3），按平台限制并发（高风险平台 xhs/dy/ks=1）。新任务超出上限时自动排队（`_task_queue`），完成后自动出队。使用 `asyncio.Lock` 防止竞态条件。

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

## 内部 API 鉴权机制

Data-API-Service 的 `/api/internal/*` 端点受 `X-API-Token` 头鉴权保护。Token 在 `api/routers/internal.py` 中通过 `_verify_internal_token()` 依赖注入校验，所有请求必须携带匹配的 `X-API-Token` 头。

### Token 配置（三处必须一致）

| 位置 | 文件 | 说明 |
|------|------|------|
| Data-API-Service | `.env` → `INTERNAL_API_TOKEN` | 校验方，模块加载时读取 |
| Crawler-Service | `.env` → `INTERNAL_API_TOKEN` | 调用方，`tools/_api_headers.py` 读取并注入 `INTERNAL_HEADERS` |
| Crawler 子进程 | 由 `crawler_manager._make_subprocess_env()` 注入 | 继承父进程的 token |

默认值：`internal-dev-token`（三处均未配置时一致，开发环境零配置可用）

### ⚠️ 前端禁止直接调用 Internal API

前端请求通过 Vite 代理转发，但**前端不持有也不应持有 `INTERNAL_API_TOKEN`**。因此前端**绝对不能**直接调用 `/api/internal/*` 端点。如果前端需要访问内部 API 的数据（如任务日志），必须通过 Crawler-Service 代理：

```
✅ 正确：前端 → /api/crawler/tasks/{id}/logs → Crawler-Service → (带 X-API-Token) → Data-API /api/internal/tasks/{id}/logs
❌ 错误：前端 → /api/internal/tasks/{id}/logs → Data-API → 403 Forbidden
```

Crawler-Service 的 `api/routers/crawler.py` 中已实现以下代理路由，前端通过这些路由间接访问 Data-API：

| 前端调用 | Crawler-Service 代理路由 | 后端实际调用 |
|----------|--------------------------|-------------|
| `GET /api/crawler/tasks` | `@router.get("/tasks")` | `GET {DATA_API}/api/internal/tasks` |
| `GET /api/crawler/tasks/{id}` | `@router.get("/tasks/{task_id}")` | `GET {DATA_API}/api/internal/tasks/{id}` |
| `DELETE /api/crawler/tasks/{id}` | `@router.delete("/tasks/{task_id}")` | `DELETE {DATA_API}/api/internal/tasks/{id}` |
| `GET /api/crawler/tasks/{id}/logs` | `@router.get("/tasks/{task_id}/logs")` | `GET {DATA_API}/api/internal/tasks/{id}/logs` |

## 常见排查场景

### 场景 1：服务进程无法 kill（Access Denied / 找不到进程）

**现象**：`netstat -ano` 显示端口被占用（如 8080/8081），但 `taskkill /F /PID xxx` 报"找不到进程"或"拒绝访问"。

**原因**：进程运行在提权上下文（管理员/WSL/Docker Desktop），当前用户无权限终止。

**正确处理**：
1. 不要反复尝试 kill — 浪费时间
2. 在空闲端口启动新服务实例：
   ```bash
   cd Crawler-Service && uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8084
   ```
3. 修改前端 `.env.development` → `VITE_CRAWLER_PROXY_TARGET` 指向新端口
4. 重启前端 `pnpm dev:web`
5. ⚠️ 注意：命令必须用 `uv run python -m uvicorn`，不能用 `uv run uvicorn`（后者在某些环境下报"Failed to canonicalize script path"）

### 场景 2：前端代理配置不生效

**现象**：修改了 `MediaCrawler-Web/.env` 但 Vite 代理仍路由到旧端口。

**原因**：Vite 的 `loadEnv(mode, ...)` 按优先级加载 env 文件，高优先级文件会覆盖低优先级：
```
.env < .env.local < .env.development < .env.development.local
```
**`.env.development` 会覆盖 `.env` 中的同名变量！**

**正确处理**：
1. 先检查所有 env 文件：`.env`、`.env.development`、`.env.local`、`.env.development.local`
2. 修改**最高优先级**的那个文件中的值
3. 修改后**必须重启** Vite dev server（env 只在启动时加载一次）

### 场景 3：前端 API 返回 403 "Forbidden: invalid internal API token"

**现象**：前端页面调用某个 API 返回 403。

**排查步骤**：
1. 检查前端是否直接调用了 `/api/internal/*`（通过浏览器 DevTools Network 面板看请求 URL）
2. 如果是 → 这是架构错误，前端不能调内部 API，需要在 Crawler-Service 添加代理路由
3. 如果前端调的是 `/api/crawler/*` 但仍然 403 → 检查 Crawler-Service 的 `INTERNAL_API_TOKEN` 是否与 Data-API-Service 一致
4. 用 curl 验证：`curl -H "X-API-Token: internal-dev-token" http://127.0.0.1:8080/api/internal/tasks?page=1`
   - 返回 200 → token 正确，问题在代理层
   - 返回 403 → token 不匹配，检查两侧 `.env` 中的 `INTERNAL_API_TOKEN`

### 场景 4：Python 服务启动命令选择

| 命令 | 结果 |
|------|------|
| `uv run uvicorn api.main:app --port 8084` | ❌ 可能报 "Failed to canonicalize script path" |
| `uv run python -m uvicorn api.main:app --port 8084` | ✅ 可靠启动 |

始终使用 `uv run python -m uvicorn` 形式。

### 场景 5：爬虫任务执行时浏览器自动打开（不定时弹出窗口）

**现象**：开启爬虫任务后，Chrome/Edge 浏览器窗口不定时自动弹出。

**根因**：`headless` 相关默认值在系统中 7 处均为 `False`（可见模式），导致浏览器以非无头模式启动。

**涉及的 4 个关键问题点**：

| # | 位置 | 问题 | 修复 |
|---|------|------|------|
| 1 | `config/base_config.py` | `HEADLESS=False` + `CDP_HEADLESS=False` | 改为 `True` |
| 2 | `config/applier.py:27` | `config.CDP_HEADLESS = config.HEADLESS` 强制同步，忽略 payload 中的 `cdp_headless` 字段 | 独立读取 `payload.get("cdp_headless")` |
| 3 | 各平台 `core.py` CDP 分支 | `headless=False` 硬编码，但仅在 `_use_headless=False` 时进入 | 逻辑正确；真正问题在上游默认值 |
| 4 | 风控配置强制 CDP | xhs/dy/ks 的 `require_cdp=True` 强制开启 CDP | 默认值修复后 CDP+headless=True 不弹窗 |

**触发条件（修复前）**：
- 用户未勾选"无头模式" → `headless=False`（默认）
- CDP 模式开启（默认 True，xhs/dy/ks 强制开启）
- 任一爬虫任务启动 → 浏览器弹窗

**浏览器弹窗的完整决策链**：
```
配置默认值(headless=False) → applier.py强制同步(cdp_headless=headless)
→ 风控配置强制CDP(高风险平台) → 平台core判断(CDP+非无头)
→ launch_browser_with_cdp(headless=False) → Chrome窗口弹出
```

**修复涉及的文件（10 个）**：`config/base_config.py`, `config/applier.py`, `api/schemas/crawler.py`, `api/schemas/config_mgmt.py`(Crawler), `api/routers/crawler.py`, `engine/task_executor.py`, `Data-API/api/schemas/config_mgmt.py`, `Data-API/services/config_service.py`, `Browser-Service/services/browser_pool.py`, `Browser-Service/.env.example`
