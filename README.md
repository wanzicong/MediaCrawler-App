# MediaCrawler

多平台自媒体数据采集工具，支持 **小红书、抖音、快手、B站、微博、贴吧、知乎** 七大平台的内容与评论抓取。

基于 Playwright 浏览器自动化 + CDP 协议控制真实浏览器实现反检测，提供现代化 Web 管理控制台。

## 功能特性

- **多平台支持** — 小红书 / 抖音 / 快手 / B站 / 微博 / 贴吧 / 知乎
- **反检测** — CDP 协议控制真实 Chrome/Edge 浏览器，模拟真人操作
- **Web 控制台** — React 前端，实时日志、任务管理、数据查询
- **AI 对话** — 集成 DeepSeek，支持会话管理 + 记忆管理
- **AI 评论分析** — 一键分析评论情感、关键观点、热点话题
- **AI 关键词裂变** — 输入种子词自动生成长尾词/相关词/问句词
- **关键词管理** — 分组管理、批量导入、直接关联爬虫任务
- **配置方案** — 可复用的爬虫配置预设，一键切换

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 浏览器自动化 | Playwright + CDP |
| 数据库 | MySQL 8.0 + SQLAlchemy (async) |
| 前端 | React 18 + TypeScript + Vite |
| UI 组件 | Ant Design 5 |
| 状态管理 | Zustand + TanStack React Query |
| AI | DeepSeek API |
| 包管理 | pnpm (monorepo) |

## 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+ & pnpm
- Docker Desktop（运行 MySQL）
- Chrome 或 Edge 浏览器

### 2. 启动 MySQL

```bash
pnpm db:up
```

MySQL 默认配置：`root / 123456`，数据库 `media_crawler`，端口 `3306`

### 3. 安装依赖

```bash
pnpm install        # 前端依赖
pnpm install:api    # Python 依赖 (uv sync)
```

### 4. 配置 AI (可选)

在 `MediaCrawler-Api/.env` 中设置：

```env
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

### 5. 启动开发服务

```bash
pnpm dev            # 并行启动 API (8080) + 前端 (5173)
```

打开浏览器访问 `http://localhost:5173`

## 项目结构

```
MediaCrawler-App/
├── MediaCrawler-Api/          # Python 后端
│   ├── main.py                # CLI 爬虫入口
│   ├── api/                   # FastAPI WebUI 层
│   │   ├── routers/           # REST API 路由
│   │   └── services/          # 爬虫管理器、WebSocket
│   ├── media_platform/        # 各平台爬虫实现
│   ├── config/                # 全局配置模块
│   ├── database/              # SQLAlchemy ORM 模型
│   ├── store/                 # 数据存储层
│   └── services/              # 后端服务层
├── MediaCrawler-Web/          # React 前端
│   └── src/
│       ├── pages/             # 页面组件
│       ├── api/               # API 调用层
│       ├── hooks/             # 自定义 Hooks
│       ├── stores/            # Zustand 状态管理
│       └── router/            # 路由配置
├── sql/                       # 数据库初始化 SQL
├── scripts/                   # 工具脚本
└── docker-compose.yml         # MySQL 容器定义
```

## 命令行使用

```bash
cd MediaCrawler-Api

# 小红书关键词搜索
uv run python main.py --platform xhs --keywords "关键词" --crawler-type search

# 抖音关键词搜索
uv run python main.py --platform dy --keywords "关键词" --crawler-type search

# 指定帖子详情抓取
uv run python main.py --platform xhs --crawler-type detail --specified-ids "帖子ID1,帖子ID2"
```

## License

MIT
