# MediaCrawler Pro 架构设计文档

## 一、设计目标

在 MediaCrawler 的基础上，Pro 版本实现以下核心能力：

1. **多任务并行执行** — 支持同时运行多个平台的多个爬虫任务，而非单任务串行
2. **断点续爬** — 任务中断后可从上一次进度恢复，避免重复爬取
3. **多账号 + IP代理池** — 账号轮换和代理 IP 配合，降低封号风险
4. **解耦 Playwright** — 浏览器引擎作为可插拔抽象层，不绑定具体实现
5. **签名服务** — 独立签名微服务，解耦各平台签名逻辑
6. **HomeFeed + 热搜榜** — 新增首页推荐流和热搜榜单爬取类型
7. **多存储后端** — 统一存储抽象，支持 DB/CSV/JSON/Excel 等自由切换
8. **视频下载器桌面端** — Electron/Tauri 桌面应用，下载自媒体平台视频

---

## 二、架构全景

```
MediaCrawler-Pro/
├── Data-API-Service/          # 数据与配置中心 (端口 8080)
├── Crawler-Service/           # 爬虫引擎 (端口 8081)
│   ├── engine/                # [新] 核心引擎
│   │   ├── task_scheduler.py  # 多任务并行调度器
│   │   ├── task_executor.py   # 单任务执行器 (替代 main.py)
│   │   ├── checkpoint.py      # 断点续爬管理器
│   │   └── account_manager.py # 多账号 + IP代理池
│   ├── browser/               # [新] 浏览器抽象层
│   │   ├── base.py            # AbstractBrowser 接口
│   │   ├── playwright_impl.py # Playwright 实现
│   │   └── selenium_impl.py   # Selenium 实现 (可选)
│   ├── media_platform/        # 平台爬虫 (重构)
│   ├── store/                 # [新] 统一存储抽象
│   │   ├── base.py            # AbstractStore (增强版)
│   │   ├── db_store.py        # HTTP -> Data-API
│   │   ├── csv_store.py       # CSV
│   │   ├── excel_store.py     # Excel
│   │   └── json_store.py      # JSON/JSONL
│   └── signer/                # [新] 签名服务客户端
├── Signer-Service/            # [新] 签名微服务 (端口 8082)
├── MediaCrawler-Desktop/      # [新] 视频下载器桌面端
└── MediaCrawler-Web/          # 前端 (增强)
```

---

## 三、核心模块设计

### 3.1 TaskScheduler — 多任务并行引擎

```
┌─────────────────────────────────────────────┐
│              TaskScheduler (单例)              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Slot 1   │  │ Slot 2   │  │ Slot N   │  │
│  │ (xhs)    │  │ (bili)   │  │ (dy)     │  │
│  │ Executor │  │ Executor │  │ Executor │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│                                              │
│  等待队列: [task_4, task_5, ...]              │
│  asyncio.Semaphore 控制并发数                  │
└─────────────────────────────────────────────┘
```

关键设计：
- `max_concurrent` 可配置的并发槽位数
- 每个槽位 = 一个 `asyncio.Task` 包装的 `TaskExecutor`
- 使用 `asyncio.Semaphore(max_concurrent)` 控制并发
- 每个 `TaskExecutor` 独立的 `CheckpointManager`、`AccountManager`、`BrowserContext`
- 任务按 platform 分组，同一平台的任务自动排队（避免同平台并发冲突）

### 3.2 CheckpointManager — 断点续爬

```
Checkpoint 数据结构:
{
    "task_id": 123,
    "platform": "xhs",
    "crawler_type": "search",
    "keyword": "美食",
    "current_page": 5,           # 当前搜索页
    "crawled_note_ids": ["id1", "id2", ...],  # 已爬取的帖子 ID
    "total_crawled": 45,         # 已爬取总数
    "last_note_id": "xxx",       # 最后爬取的帖子ID（用于游标翻页）
    "comment_progress": {        # 评论爬取进度
        "note_id_1": 10,         # 已爬取评论数
        "note_id_2": 5
    },
    "updated_at": "2025-05-28T10:00:00",
    "status": "running"
}
```

关键设计：
- 每爬完一页/一个笔记后自动保存 checkpoint
- 任务启动时先检查是否有未完成的 checkpoint
- 支持恢复到指定粒度（页级别/笔记级别/评论级别）
- checkpoint 持久化到 MySQL（通过 Data-API）
- 提供 `--resume` 和 `--checkpoint-file` CLI 参数

### 3.3 AccountManager — 多账号 + IP代理池

```
AccountManager:
  ├── accounts: List[Account]           # 可用账号池
  │   ├── phone / username
  │   ├── cookies (加密存储)
  │   ├── last_used
  │   ├── daily_request_count
  │   ├── status: active | cooling | banned
  │   └── platform_bindings
  │
  ├── proxy_pool: ProxyIpPool           # IP 代理池
  │
  ├── 调度策略:
  │   ├── RoundRobin 轮询
  │   ├── LeastUsed 最少使用
  │   └── CoolingOff 冷却时间
  │
  └── 绑定关系: account <-> proxy 可选绑定
```

关键设计：
- 账号冷却机制：超过频率限制后自动进入冷却期
- 账号-代理绑定：一个账号绑定一个代理 IP，模拟真实用户
- 账号状态监控：被风控/封禁时自动标记、告警
- Cookie 加密存储，通过 Data-API 管理
- 支持账号池热加载

### 3.4 Browser 抽象层

```
AbstractBrowser (Protocol):
    async create_context(proxy, user_agent) -> BrowserContext
    async new_page(context) -> Page
    async navigate(page, url)
    async wait_for_selector(page, selector)
    async get_cookies(context) -> List[Dict]
    async close_context(context)
    async cleanup()

实现:
    PlaywrightBrowser   — 基于 Playwright (CDP 模式 + 标准模式)
    SeleniumBrowser     — 基于 Selenium (备选)
```

关键设计：
- 不再在 AbstractCrawler 中硬编码 Playwright 类型导入
- 爬虫只依赖 `AbstractBrowser` 接口
- 浏览器创建、CDP 连接逻辑统一在 Browser 实现层
- 每个 TaskExecutor 拥有独立的 BrowserContext，实现资源隔离

### 3.5 签名服务

```
Signer-Service/ (独立 FastAPI, 端口 8082)
├── routers/
│   ├── xhs_sign.py       # 小红书签名 (xs, xt, x-s-common 等)
│   ├── dy_sign.py        # 抖音签名 (X-Bogus, _signature 等)
│   └── ks_sign.py        # 快手签名
├── signers/              # 各平台签名实现
└── api/main.py           # FastAPI 入口
```

关键设计：
- 独立进程，可与爬虫分离部署
- 爬虫通过 HTTP/gRPC 调用签名服务
- 签名算法可实现动态更新（JS 虚拟机或纯 Python 实现）
- 支持签名缓存减少重复计算

### 3.6 多存储后端

```
StoreFactory.create(platform, save_option) -> AbstractStore

AbstractStore (增强):
    store_content(item)
    store_comment(item)
    store_creator(item)
    store_homefeed(item)      # [新]
    store_trending(item)      # [新]
    flush()
    close()

实现:
    HttpStore     -> HTTP → Data-API → MySQL
    CsvStore      -> CSV 文件
    ExcelStore    -> Excel 文件
    JsonStore     -> JSON/JSONL 文件
```

### 3.7 HomeFeed + 热搜榜爬虫

```
新增爬取类型:
    CRAWLER_TYPE = "homefeed"  # 首页推荐流
    CRAWLER_TYPE = "trending"  # 热搜榜单

AbstractCrawler 新增方法:
    async def crawl_homefeed(self)    # 爬取首页推荐
    async def crawl_trending(self)    # 爬取热搜榜单
```

---

## 四、数据流变更

```
用户配置任务 (WebUI / CLI)
  → POST /api/crawler/start (可多个)
  → Crawler-Service: TaskScheduler
     → 如果没有空闲槽位 → 进入等待队列
     → 如果有空闲槽位 → Semaphore.acquire()
        → TaskExecutor(task_id).run()
           ├── CheckpointManager: 检查断点 → 恢复进度
           ├── AccountManager: 分配账号 + IP
           ├── Browser: 创建浏览器上下文
           ├── Crawler: 执行爬取
           │   ├── 每页/每笔记后: CheckpointManager.save()
           │   └── 需要签名时: Signer-Service HTTP 调用
           ├── Store: 写入数据
           └── finally: 释放账号、关闭浏览器、Semaphore.release()
        → dequeue 下一个等待任务
```

---

## 五、实现优先级

| 优先级 | 模块 | 影响范围 | 工作量 |
|--------|------|----------|--------|
| P0 | TaskScheduler (多任务并行) | 核心引擎 | 2-3天 |
| P0 | CheckpointManager (断点续爬) | 核心流程 | 1-2天 |
| P0 | AccountManager (多账号+IP) | 稳定性 | 2-3天 |
| P1 | Browser 抽象层 | 解耦 | 1-2天 |
| P1 | 签名服务 | 解耦 | 2-3天 |
| P1 | 多存储后端 | 灵活性 | 1天 |
| P2 | HomeFeed + 热搜榜 | 新功能 | 3-5天 |
| P2 | 视频下载器桌面端 | 新应用 | 5-7天 |

