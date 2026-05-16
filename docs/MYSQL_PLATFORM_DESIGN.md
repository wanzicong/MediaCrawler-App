# MediaCrawler 平台化设计（MySQL 中心化）

## 1. 产品定位

| 维度 | 决策 |
|------|------|
| 用户 | 运营/分析人员，通过浏览器完成全部操作 |
| 数据 | 爬取结果默认写入 **MySQL**（`save_data_option=db`） |
| 配置 | 存 **crawler_profile** 表，API 读写，不再改 `config/*.py` |
| 任务 | 每次启动生成 **crawler_task** 快照，子进程 `--task-id` 加载 |
| 引导 | 仅 `.env` 保留 MySQL 连接串（bootstrap） |

## 2. 信息架构（Web）

```
概览 ── 系统健康 / DB / 当前任务
配置方案 ── 列表 + 编辑（基础 | 高级）+ 设为默认
爬虫任务 ── 选方案 → 覆盖参数 → 启动 / 停止 / 日志
数据中心 ── 按平台 + 内容|评论|创作者 分页查询（MySQL）
```

## 3. 数据模型

- **crawler_profile**：可复用配置方案（JSON payload）
- **crawler_task**：单次运行快照与状态（pending/running/completed/failed）
- **业务表**：沿用现有 `xhs_note` 等 21+ 表

## 4. API 契约

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/profiles` | 方案列表 |
| POST | `/api/config/profiles` | 新建 |
| GET/PUT/DELETE | `/api/config/profiles/{id}` | 详情/更新/删除 |
| POST | `/api/config/profiles/{id}/default` | 设为默认 |
| GET | `/api/config/schema` | 表单字段元数据 |
| POST | `/api/system/init-database` | 建库建表 + 种子方案 |
| GET | `/api/data/db/platforms` | 可查询平台 |
| GET | `/api/data/db/{platform}/{kind}` | 分页数据 |
| POST | `/api/crawler/start` | `profile_id` + overrides → 创建 task |

## 5. 实现要点

- 配置 API 始终走 `get_mysql_session()`，与 `SAVE_DATA_OPTION` 无关
- 爬虫子进程：`main.py --task-id N` → 读库 → `apply_crawler_payload` → `parse_cmd()`
- 媒体文件、浏览器 Profile 仍落盘；库中存结构化字段

## 6. 分期

- **本期（MVP）**：上述 API + Web 三页改造 + 默认 db
- **下期**：多用户、Cookie 加密入库、媒体 OSS、Alembic 迁移
