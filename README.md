# MediaCrawler

多平台自媒体数据采集工具，支持 **小红书、抖音、快手、B站、微博、贴吧、知乎** 七大平台的内容与评论抓取。

基于 Playwright 浏览器自动化 + CDP 协议控制真实浏览器实现反检测，提供现代化 Web 管理控制台。

## 功能特性

- **多平台支持** — 小红书 / 抖音 / 快手 / B站 / 微博 / 贴吧 / 知乎
- **反检测** — CDP 协议控制真实 Chrome/Edge 浏览器，模拟真人操作
- **Web 控制台** — React 前端，实时日志、任务管理、数据查询
- **AI 对话** — 集成 DeepSeek，支持会话管理 + 记忆管理
- **多任务并发** — 经典子进程模式 + Pro 进程内调度，最多 3 并发
- **配置方案** — 可复用的爬虫配置预设，一键切换

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 浏览器自动化 | Playwright + CDP |
| 数据库 | MySQL 8.0 + SQLAlchemy (async) |
| 前端 | React 18 + TypeScript + Vite (端口 10001) |
| UI 组件 | Ant Design 5 |
| 包管理 | pnpm (monorepo) |

## 服务架构

| 服务 | 端口 | 职责 |
|------|------|------|
| Data-API-Service | 8080 | 数据库、配置、AI、内部 API |
| Crawler-Service | 8081 | 爬虫控制、WebSocket、引擎 |
| Browser-Service | 9500 | Chrome/Edge 实例池 |
| Signer-Service | 8082 | xhs/dy 签名 |
| MediaCrawler-Web | 10001 | React 控制台 |

## 快速开始

### 1. 环境要求

- Python 3.11+、uv
- Node.js 18+ & pnpm 9+
- Docker Desktop（MySQL + Redis）
- Chrome 或 Edge 浏览器

### 2. 启动基础设施

```bash
pnpm db:up    # 启动 MySQL + Redis，自动 ORM 建表
```

MySQL：`root / 123456`，数据库 `media_crawler`，端口 `3306`

### 3. 安装依赖

```bash
pnpm install        # 前端依赖
pnpm install:api    # 四个 Python 服务 uv sync
```

### 4. 配置环境变量

复制根目录 `.env.example` 为 `.env`，至少配置：

```env
INTERNAL_API_TOKEN=请改为强随机值
DEEPSEEK_API_KEY=你的Key（可选）
SIGNER_FAIL_FAST=false   # 生产建议 true
```

### 5. 启动开发服务

```bash
pnpm dev    # 并行启动 4 后端 + 前端
```

打开 `http://localhost:10001`

## 项目结构

```
MediaCrawler-App/
├── Data-API-Service/     # 数据 & 配置中心 (8080)
├── Crawler-Service/      # 爬虫引擎 (8081)
├── Browser-Service/      # 浏览器池 (9500)
├── Signer-Service/       # 签名服务 (8082)
├── MediaCrawler-Web/     # React 前端 (10001)
├── sql/                  # Docker 仅初始化数据库（表由 ORM 管理）
└── scripts/              # MySQL 管理脚本
```

## 常用命令

```bash
pnpm dev              # 全部服务
pnpm dev:api          # 仅后端
pnpm db:init          # 手动 ORM 建表 + 补齐列
pnpm db:reset         # 清空数据卷并重新初始化

# 命令行爬虫
cd Crawler-Service
uv run python main.py --platform xhs --keywords "关键词" --crawler-type search
```

## 生产部署检查清单

- [ ] 修改 `INTERNAL_API_TOKEN` 为强随机值
- [ ] 设置 `SIGNER_FAIL_FAST=true`
- [ ] 修改 MySQL/Redis 默认密码
- [ ] 配置反向代理（/api → 8080，/api/crawler → 8081）
