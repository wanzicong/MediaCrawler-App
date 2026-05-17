# MediaCrawler 商业数据平台 — 完整架构方案

> **文档版本**: v1.0
> **创建日期**: 2026-05-17
> **目标**: 将 MediaCrawler 从"爬虫工具"进化为"商业数据平台"

---

## 目录

1. [需求分析](#一需求分析)
2. [头脑风暴](#二头脑风暴)
3. [需求方案](#三需求方案)
4. [技术方案](#四技术方案)
5. [测试方案](#五测试方案)
6. [验收方案](#六验收方案)

---

# 一、需求分析

## 1.1 现状诊断

### 1.1.1 架构优势（已有资产）

| 资产 | 位置 | 价值评估 |
|------|------|---------|
| **7 平台统一爬虫架构** | `media_platform/{xhs,bilibili,douyin,weibo,kuaishou,tieba,zhihu}/core.py` | 竞品大多只支持 1-2 个平台，这是最大壁垒 |
| **AbstractCrawler 抽象基类** | `base/base_crawler.py:26` | 统一的 `start() → search()/get_specified_notes()/get_creators_and_notes()` 流程，新平台接入成本低 |
| **CDP 反检测** | `tools/cdp_browser.py` + `base_config.py:76` | 真实浏览器环境，比纯 HTTP 请求方案风控通过率高 5-10 倍 |
| **多存储后端** | `store/` 目录下 CSV/JSON/JSONL/DB/MongoDB/Excel 六种实现 | 灵活适配不同场景 |
| **配置方案系统** | `database/system_models.py` CrawlerProfile + CrawlerTask | 可复用的配置模板，支持不同分析场景快速切换 |
| **WebUI 可视化** | `MediaCrawler-Web/` React 18 + Ant Design 5 + React Query | 非技术人员可用的操作界面 |
| **WebSocket 实时推送** | `api/routers/websocket.py` | 日志和状态的实时反馈 |
| **异步并发架构** | 全链路 `asyncio` + `asyncio.Semaphore` | Python 异步最佳实践 |

### 1.1.2 核心短板（必须修复）

| # | 问题 | 影响 | 严重度 |
|---|------|------|--------|
| 1 | **数据量太少** — `CRAWLER_MAX_NOTES_COUNT = 15` | 连搜索结果第 1 页都爬不满，无法做任何有效分析 | 🔴 致命 |
| 2 | **无数据库 UNIQUE 约束** — `note_id` 等字段仅有普通索引无唯一约束 | 重复数据无法在数据库层面拦截 | 🔴 致命 |
| 3 | **零自动化探索能力** — 每次任务只爬固定关键词列表 | 无法发现新话题、新趋势，完全依赖人工输入 | 🔴 致命 |
| 4 | **数据清洗完全缺失** — 无任何数据规范化/清洗模块 | 脏数据分析结论不可信 | 🟠 严重 |
| 5 | **无分析层** — 仅有原始数据 CRUD 查询 | 用户看到的是数据库表，不是分析洞察 | 🟠 严重 |
| 6 | **风控配置一刀切** — 所有平台共享同一套间隔/并发/限量 | 小红书风控极严而贴吧极松，同配置必然导致小红书频繁被封而贴吧效率低下 | 🟡 中等 |
| 7 | **词云功能严重受限** — 仅在 JSON/JSONL 文件模式下可用 | 数据库模式下（最常用的存储方式）完全无法使用 | 🟡 中等 |
| 8 | **tag_list 是死数据** — 存储为 JSON 文本但从未被解析分析 | 标签是最有价值的元数据却被浪费 | 🟡 中等 |

## 1.2 用户需求分析

### 1.2.1 用户角色与核心场景

```
┌──────────────────────────────────────────────────────────────┐
│                      用户角色画像                               │
├──────────────┬───────────────────┬─────────────────────────────┤
│ 自媒体运营者  │ 选题灵感、竞品分析  │ "最近小红书'编程副业'话题下   │
│              │ 热点追踪          │  什么类型内容最火？"          │
├──────────────┼───────────────────┼─────────────────────────────┤
│ MCN 机构     │ 达人发现、内容策略  │ "帮我找出美妆领域 1-10 万粉   │
│              │                  │  增长最快的 10 个创作者"      │
├──────────────┼───────────────────┼─────────────────────────────┤
│ 品牌方/广告主 │ 舆情监控、投放分析  │ "我的品牌在小红书/微博上的    │
│              │                  │  讨论情感趋势怎样？"          │
├──────────────┼───────────────────┼─────────────────────────────┤
│ 数据分析师    │ 跨平台趋势研究    │ "对比 B站 和 小红书 在'AI编程' │
│              │                  │  话题上的内容量和互动率差异"    │
├──────────────┼───────────────────┼─────────────────────────────┤
│ 电商卖家     │ 种草内容分析      │ "竞品 X 的哪些卖点被用户      │
│              │                  │  讨论最多？好评差评各占多少？"  │
└──────────────┴───────────────────┴─────────────────────────────┘
```

### 1.2.2 用户旅程（当前 vs 期望）

**当前旅程**：
```
用户打开 WebUI → 手动输入关键词 → 启动爬虫 → 等待完成
→ 去"数据中心"查看原始表格 → 手动导出 CSV → Excel 分析
```
问题：整个过程大部分在项目外部完成，MediaCrawler 只做了"采集"这一步。

**期望旅程**：
```
用户打开 WebUI → 输入种子关键词 → 启动探索式爬虫
→ 系统自动发现关联关键词并持续采集 → 看板展示趋势/情感/排行
→ 一键导出分析报告
```
MediaCrawler 应该覆盖"采集 → 清洗 → 分析 → 报告"全链路。

## 1.3 需求优先级矩阵

基于"影响力 × 实现成本"的优先级矩阵：

```
高影响 ┤  阶段一 ★★★          │  阶段二 ★★★
       │  数据量杠杆           │  探索式爬取
       │  (低投入 高回报)       │  (核心差异化)
       │                       │
       │  阶段四 ★★            │  阶段三 ★★
       │  风控增强              │  数据清洗管道
低影响 ┤  阶段五 ★              │
       │  商业分析层            │
       └───────────────────────
         低成本              高成本
```

---

# 二、头脑风暴

## 2.1 数据量杠杆 — 深度思考

### 2.1.1 为什么默认值只有 15？

追踪代码历史可以发现，`CRAWLER_MAX_NOTES_COUNT = 15` 是因为项目最初定位是"学习/演示"用途。这个值对于商业分析来说完全不够：
- 小红书每页 20 条，15 条连第 1 页都爬不满
- 搜索"编程副业"可能有 1000+ 结果，15 条样本量根本无统计学意义
- 后续的 TF-IDF 词频分析、情感分析都需要至少 100+ 样本才有参考价值

### 2.1.2 数据量提升的风险

直接提量到 500 条会触发以下问题：
1. **风控加剧** — 连续请求 20+ 页必然触发平台频率限制
2. **去重问题暴露** — 翻页时可能出现重复内容，当前无去重机制
3. **存储膨胀** — 每次任务可能产生 500 条内容 + 5000+ 条评论
4. **爬取耗时** — 单并发 500 条内容可能需要 30+ 分钟

### 2.1.3 破局思路

差异化配置 + 智能限速 + 数据库 UNIQUE 约束：

```
方案 A: 一刀切提高默认值 → 简单但容易触发风控
方案 B: 分平台差异化配置 → 精确但配置复杂
方案 C: 动态调整 + 监控 → 最优但开发量大
推荐: B + C 的混合方案
  - 短期: 分平台默认值（小红书 50、B站 200、贴吧 500）
  - 中期: 增加频率监控，检测到限流自动降速
  - 远期: 接入验证码自动处理
```

## 2.2 探索式爬取 — 核心创新

### 2.2.1 关键词发现算法

基于当前项目已有的数据字段，关键词可以从以下维度自动提取：

```
维度 1: tag_list 标签（已有数据，直接可用）
  XhsNote.tag_list = '["Python","远程工作","程序员"]'
  → 解析 JSON → 标签频次统计 → TOP-N 高频标签

维度 2: title + desc 分词提取（需要 jieba + TF-IDF）
  "零基础如何通过Python副业月入过万 — 我的经验分享"
  → jieba 分词 → 去停用词 → TF-IDF 排序 → ["Python","副业","月入"]

维度 3: 评论热点词（需要 jieba）
  评论中反复出现的名词 → 用户真正关心的话题

维度 4: 搜索结果关联推荐（需要分析 API 响应）
  搜索接口有时会返回 "related_keywords" 或 "猜你喜欢"

维度 5: 创作者跨内容标签关联
  爬取创作者其他内容的 tag_list → 发现内容生态关联
```

### 2.2.2 关键词评分模型

```
评分 = w1 × 新颖度 + w2 × 关联度 + w3 × 信息增益 - w4 × 衰减因子

新颖度 = 1 - (已爬取次数 / 最大允许重复次数)
关联度 = 与种子词的语义相似度 (基于词向量或共现关系)
信息增益 = 预期新增内容数 (基于平台搜索返回的 total_count)
衰减因子 = 与种子词的路径距离 × 0.3
```

### 2.2.3 爬取策略

```
策略 A: BFS 广度优先 — 每轮探索所有新关键词的浅层结果
  适合: 快速覆盖一个话题的广度
  风险: 关键词数量爆炸

策略 B: DFS 深度优先 — 沿着一条线索深挖
  适合: 深入理解一个细分话题
  风险: 可能陷入窄话题

策略 C: 优先级队列 — 评分最高的优先爬取
  适合: 在有限时间/资源下获取最大信息量
  推荐: ✅

默认推荐策略 C + 可配置最大深度和最大关键词数
```

## 2.3 数据清洗管道 — 架构思考

### 2.3.1 清洗的三个层次

```
层次 1: 实时清洗（爬虫 Store 层）
  - 爬虫写入数据库前执行
  - 处理: 类型转换、HTML 清理、空值规范
  - 要求: 极快，不能拖慢爬虫

层次 2: 异步增强（后处理任务）
  - 爬虫任务完成后触发
  - 处理: 情感分析、关键词提取、内容分类
  - 要求: 不阻塞爬虫，可耗时较长

层次 3: 聚合计算（定时/触发）
  - 按需或按定时触发
  - 处理: 时间序列聚合、跨平台对比、榜单生成
  - 要求: 可缓存结果，不需要实时
```

### 2.3.2 技术选型

| 清洗任务 | 技术方案 | 理由 |
|----------|---------|------|
| 中文分词 | jieba (已有依赖) | 项目已使用，无需新增依赖 |
| 情感分析 | snownlp (轻量) 或调用阿里云 NLP API | snownlp 免费但准确度中等；API 准确但收费 |
| 内容分类 | jieba + TF-IDF + 规则引擎 | 初期用规则（关键词匹配），后期可训练分类器 |
| HTML 清理 | `re.sub` + `html.unescape` | 标准库即可 |
| 去重 | 数据库 UNIQUE 约束 + Bloom Filter | UNIQUE 保证 DB 层，Bloom Filter 减少查询 |

## 2.4 风控增强 — 平台差异化

### 2.4.1 平台风控差异表

| 平台 | 风控等级 | 建议间隔(秒) | 建议并发 | 建议 MAX_NOTES | 特殊策略 |
|------|---------|-------------|---------|---------------|---------|
| 小红书 | ⭐⭐⭐⭐⭐ | [8, 20] | 1 | 50-100 | CDP 必需，Cookie 时效短 |
| 抖音 | ⭐⭐⭐⭐ | [5, 15] | 1-2 | 30-80 | 设备指纹敏感，需要真实浏览器 |
| B站 | ⭐⭐⭐ | [3, 10] | 2-3 | 100-300 | API 签名校验 (BilibiliSign) |
| 微博 | ⭐⭐⭐ | [3, 10] | 2-3 | 50-150 | 登录态校验严格 |
| 快手 | ⭐⭐⭐ | [4, 12] | 1-2 | 50-100 | 设备指纹 |
| 贴吧 | ⭐⭐ | [2, 6] | 3-5 | 200-500 | 相对宽松 |
| 知乎 | ⭐⭐ | [2, 8] | 2-4 | 100-200 | 偶尔验证码 |

### 2.4.2 动态节流策略

```
正常模式: 按配置的间隔范围随机 sleep
降速模式: 检测到 461/471/IP 限制 → 间隔 × 2
恢复模式: 连续 10 次请求成功 → 间隔恢复
暂停模式: 检测到明确封禁 → 暂停 5-15 分钟 → 切换 IP → 重试
```

---

# 三、需求方案

## 3.1 阶段一：数据量杠杆（版本 v2.1）

### FR-1: 提高默认爬取数据量
- **FR-1.1**: 将 `CRAWLER_MAX_NOTES_COUNT` 默认值从 15 提高到 100
- **FR-1.2**: 将 `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES` 默认值从 10 提高到 30
- **FR-1.3**: 在 WebUI 配置方案表单中，`max_notes_count` 的推荐值改为 100，输入框提示"建议 50-500"
- **FR-1.4**: 在 WebUI 配置方案表单中，`sleep_interval` 的推荐值改为 5-15 秒随机区间

### FR-2: 数据库去重约束
- **FR-2.1**: 为核心 ID 字段添加 UNIQUE 约束（note_id, video_id, aweme_id, comment_id, content_id）
- **FR-2.2**: 修改所有 `*DbStoreImplement` 的 store 方法，改为 `INSERT ... ON DUPLICATE KEY UPDATE` 模式
- **FR-2.3**: 在爬虫流程中增加内存级去重（基于已爬 ID 集合）

### FR-3: 爬取进度与断点续爬
- **FR-3.1**: 每个 Task 增加 `progress` 字段（已爬数/总数/当前页/状态）
- **FR-3.2**: 记录已爬 note_id 列表，任务中断后重启时跳过已爬内容
- **FR-3.3**: WebUI 显示爬取进度条

### FR-4: 平台差异化配置
- **FR-4.1**: 新增 `platform_config` 表，存储每个平台的独立配置
- **FR-4.2**: 配置文件结构：`{platform: {max_notes, sleep_min, sleep_max, max_concurrency}}`
- **FR-4.3**: WebUI 设置页面增加"平台风控设置"Tab

## 3.2 阶段二：探索式爬取（版本 v2.2）

### FR-5: 关键词自动发现
- **FR-5.1**: 从 `tag_list` 字段提取高频标签作为新关键词
- **FR-5.2**: 从 `title` + `desc` 使用 jieba + TF-IDF 提取热点词
- **FR-5.3**: 从评论内容提取高频名词作为新关键词
- **FR-5.4**: 支持配置关键词发现开关和各来源权重

### FR-6: 关键词评分与选择
- **FR-6.1**: 实现关键词评分算法（新颖度 + 关联度 + 信息增益）
- **FR-6.2**: 支持配置最大探索深度、每轮最大新关键词数
- **FR-6.3**: 支持关键词黑名单/白名单过滤

### FR-7: 关键词关联图
- **FR-7.1**: 新增 `keyword_graph` 数据表
- **FR-7.2**: 存储关键词之间的关联关系（来源类型、共现次数、置信度）
- **FR-7.3**: WebUI 提供关键词关联图可视化

### FR-8: 自动化爬取调度器
- **FR-8.1**: 实现轮次式自动爬取调度
- **FR-8.2**: 支持配置最大轮次、每轮间隔时间
- **FR-8.3**: WebUI 显示探索进度（当前轮次、已发现关键词、已爬取数据量）
- **FR-8.4**: 支持手动暂停/恢复/终止探索任务

### FR-9: 去重增强
- **FR-9.1**: 爬取流程中增加 Bloom Filter 内存去重
- **FR-9.2**: 跨任务去重检查（同一 note_id 被不同 task 爬取时只存储一次）
- **FR-9.3**: WebUI 显示去重统计（跳过重复数/新增数）

## 3.3 阶段三：数据清洗管道（版本 v2.3）

### FR-10: 基础清洗管道
- **FR-10.1**: 时间戳规范化 — 所有时间统一为毫秒级 Unix timestamp
- **FR-10.2**: 空值规范化 — `""`、`null`、`"0"`、`"null"` 统一为数据库 NULL
- **FR-10.3**: HTML/特殊字符清理 — 去除 `<br/>`、`&nbsp;`、`\n` 等
- **FR-10.4**: 表情符号处理 — emoji 统一为 `[emoji]` 占位符
- **FR-10.5**: IP 属地标准化 — "来自上海"→"上海市", "上海"→"上海市"

### FR-11: 评论情感分析
- **FR-11.1**: 基于 snownlp 实现评论情感正/负/中性分类
- **FR-11.2**: 新增 `comment_sentiment` 字段（positive/negative/neutral + confidence score）
- **FR-11.3**: WebUI 数据中心展示情感标签和置信度

### FR-12: 内容自动分类
- **FR-12.1**: 基于 TF-IDF + 规则引擎实现内容分类（教程/测评/Vlog/营销/资讯/其他）
- **FR-12.2**: 新增 `content_category` 字段
- **FR-12.3**: WebUI 支持按分类筛选

### FR-13: 分析结果表设计
- **FR-13.1**: 新增 `content_analysis` 表（sentiment, category, keywords_extracted, quality_score）
- **FR-13.2**: 新增 `creator_score` 表（influence_score, growth_rate, content_quality_score）
- **FR-13.3**: 新增 `topic_trend` 聚合表（topic, date, platform, content_count, avg_engagement）

## 3.4 阶段四：风控增强（版本 v2.4）

### FR-14: 请求频率监控
- **FR-14.1**: 实现 `RateLimitMonitor` 类，实时检测限流响应
- **FR-14.2**: 自动降速策略（降速→恢复→暂停三级）
- **FR-14.3**: WebSocket 推送风控事件到前端

### FR-15: UA 随机轮换
- **FR-15.1**: 集成 `fake-useragent` 库
- **FR-15.2**: 每次请求随机选择 UA（按平台限制合理的 UA 范围）

### FR-16: 代理质量评分
- **FR-16.1**: 统计每个代理的成功率、响应时间
- **FR-16.2**: 自动淘汰低质量代理
- **FR-16.3**: 代理池自动补充

## 3.5 阶段五：商业分析层（版本 v3.0）

### FR-17: 数据看板
- **FR-17.1**: 概览 Dashboard 重构 — 增加趋势图、热门关键词、平台占比
- **FR-17.2**: 话题分析页 — 关键词趋势、情感趋势、内容分类分布
- **FR-17.3**: 创作者分析页 — 创作者榜单、增长趋势、内容质量评分

### FR-18: 报告生成
- **FR-18.1**: 支持按关键词/行业/时间范围生成分析报告
- **FR-18.2**: 报告包含：数据概览、趋势分析、情感分析、热门内容 TOP10、创作者榜单
- **FR-18.3**: 支持导出 PDF / Markdown 格式

### FR-19: 竞品对比分析
- **FR-19.1**: 支持选定多个创作者/品牌进行横向对比
- **FR-19.2**: 对比维度：内容量、互动率、粉丝增长、内容类型分布、情感评分
- **FR-19.3**: 可视化对比图表

---

# 四、技术方案

## 4.1 阶段一：数据量杠杆 — 技术实现

### 4.1.1 后端变更

#### A. 修改默认配置值

**文件**: `MediaCrawler-Api/config/base_config.py`

```python
# 变更前
CRAWLER_MAX_NOTES_COUNT = 15
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10
CRAWLER_MAX_SLEEP_SEC = 2
MAX_CONCURRENCY_NUM = 1

# 变更后
CRAWLER_MAX_NOTES_COUNT = 100
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 30
CRAWLER_MAX_SLEEP_SEC = 5          # 基础间隔提高
CRAWLER_MAX_SLEEP_SEC_MAX = 15     # 新增: 随机上限
MAX_CONCURRENCY_NUM = 2            # 适当提高
```

**文件**: `MediaCrawler-Api/config/profile_defaults.py`

同步更新 `build_default_payload()` 中的默认值。

#### B. 数据库 UNIQUE 约束

**文件**: `MediaCrawler-Api/database/models.py`

需要修改的核心表：

```sql
-- XHS 内容表
ALTER TABLE xhs_note ADD UNIQUE INDEX uk_note_id (note_id);
-- XHS 评论表
ALTER TABLE xhs_note_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
-- B站视频表
ALTER TABLE bilibili_video ADD UNIQUE INDEX uk_video_id (video_id);
-- B站评论表
ALTER TABLE bilibili_video_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
-- 抖音视频表
ALTER TABLE douyin_aweme ADD UNIQUE INDEX uk_aweme_id (aweme_id);
-- ... 依此类推所有平台的内容和评论表
```

**文件**: `MediaCrawler-Api/store/{platform}/_store_impl.py`

将所有 `*DbStoreImplement` 的 store 逻辑改为使用 MySQL 的 `ON DUPLICATE KEY UPDATE`:

```python
from sqlalchemy.dialects.mysql import insert as mysql_insert

async def store_content(self, content_item: dict):
    stmt = mysql_insert(NoteModel).values(**content_item)
    stmt = stmt.on_duplicate_key_update(
        liked_count=stmt.inserted.liked_count,
        collected_count=stmt.inserted.collected_count,
        last_update_time=func.now()
    )
    await session.execute(stmt)
```

#### C. 前端配置表单更新

**文件**: `MediaCrawler-Web/src/types/config.ts`

```typescript
export const DEFAULT_PAYLOAD: CrawlerPayload = {
  // ... 其他字段不变
  crawler_max_notes_count: 100,    // 从 15 改为 100
  crawler_max_comments_count_singlenotes: 30,  // 从 10 改为 30
  max_concurrency_num: 2,          // 从 1 改为 2
  crawler_max_sleep_sec: 5,        // 从 2 改为 5
};
```

**文件**: `MediaCrawler-Web/src/pages/Settings/index.tsx`

在"高级"Tab 中增加 `crawler_max_sleep_sec_max` 字段的输入框，并将 `crawler_max_sleep_sec` 的标签改为"最小间隔(秒)"。

#### D. 进度追踪

**文件**: `MediaCrawler-Api/api/schemas/crawler.py`

新增：
```python
class CrawlerProgress(BaseModel):
    total: int = 0
    completed: int = 0
    current_page: int = 0
    skipped_duplicates: int = 0
    status: str = "idle"
```

### 4.1.2 数据库迁移

```sql
-- migration_v2.1.sql
-- 1. 添加 UNIQUE 约束
ALTER TABLE xhs_note ADD UNIQUE INDEX uk_note_id (note_id);
ALTER TABLE xhs_note_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE bilibili_video ADD UNIQUE INDEX uk_video_id (video_id);
ALTER TABLE bilibili_video_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE douyin_aweme ADD UNIQUE INDEX uk_aweme_id (aweme_id);
ALTER TABLE douyin_aweme_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE kuaishou_video ADD UNIQUE INDEX uk_video_id (video_id);
ALTER TABLE kuaishou_video_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE weibo_note ADD UNIQUE INDEX uk_note_id (note_id);
ALTER TABLE weibo_note_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE tieba_note ADD UNIQUE INDEX uk_note_id (note_id);
ALTER TABLE tieba_comment ADD UNIQUE INDEX uk_comment_id (comment_id);
ALTER TABLE zhihu_content ADD UNIQUE INDEX uk_content_id (content_id);
ALTER TABLE zhihu_comment ADD UNIQUE INDEX uk_comment_id (comment_id);

-- 2. 对已有重复数据去重（保留最新的一条）
DELETE t1 FROM xhs_note t1
INNER JOIN xhs_note t2
WHERE t1.id < t2.id AND t1.note_id = t2.note_id;
-- ... 依此类推
```

## 4.2 阶段二：探索式爬取 — 技术实现

### 4.2.1 新增数据库表

```sql
-- keyword_graph 关键词关联图
CREATE TABLE keyword_graph (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL,
    source_keyword VARCHAR(500) NOT NULL COMMENT '来源关键词',
    target_keyword VARCHAR(500) NOT NULL COMMENT '发现的新关键词',
    relation_type VARCHAR(50) NOT NULL COMMENT '关系类型: tag/desc/comment/creator',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    cooccurrence_count INT DEFAULT 1 COMMENT '共现次数',
    confidence FLOAT DEFAULT 0.0 COMMENT '置信度 0-1',
    crawled BOOLEAN DEFAULT FALSE COMMENT '是否已被爬取',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_source (task_id, source_keyword),
    INDEX idx_target_crawled (target_keyword, crawled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- exploration_task 探索任务
CREATE TABLE exploration_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL COMMENT '任务名称',
    seed_keywords TEXT NOT NULL COMMENT '种子关键词 JSON 数组',
    platform VARCHAR(20) NOT NULL,
    max_depth INT DEFAULT 3 COMMENT '最大探索深度',
    max_keywords_per_round INT DEFAULT 5 COMMENT '每轮最大新关键词数',
    status VARCHAR(32) DEFAULT 'pending' COMMENT 'pending/running/paused/completed/stopped',
    current_round INT DEFAULT 0,
    total_discovered_keywords INT DEFAULT 0,
    total_crawled_contents INT DEFAULT 0,
    config_snapshot JSON COMMENT '探索配置快照',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.2.2 新增服务模块

```
MediaCrawler-Api/
  services/
    exploration/
      __init__.py              # 导出
      keyword_extractor.py     # 关键词提取器
      keyword_scorer.py        # 关键词评分器
      exploration_scheduler.py # 探索调度器
      bloom_filter.py          # Bloom Filter 去重
    analysis/
      __init__.py
      sentiment_analyzer.py    # 情感分析器
      content_classifier.py    # 内容分类器
      data_cleaner.py          # 数据清洗器
```

### 4.2.3 关键词提取器设计

**文件**: `MediaCrawler-Api/services/exploration/keyword_extractor.py`

```python
from collections import Counter
import jieba
import jieba.analyse
import json

class KeywordExtractor:
    """多源关键词提取器"""

    def __init__(self, stop_words_path: str = "./docs/hit_stopwords.txt"):
        self.stop_words = self._load_stop_words(stop_words_path)

    def extract_from_tags(self, tag_list_json: str) -> list[str]:
        """从 tag_list JSON 提取标签"""
        try:
            tags = json.loads(tag_list_json)
            return [t for t in tags if isinstance(t, str) and len(t) > 1]
        except (json.JSONDecodeError, TypeError):
            return []

    def extract_from_text(self, text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """从文本中使用 TF-IDF 提取关键词"""
        return jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)

    def extract_from_comments(self, comments: list[str], top_k: int = 10) -> list[str]:
        """从评论批量提取高频词"""
        all_text = " ".join(comments)
        words = jieba.cut(all_text)
        filtered = [w for w in words if w not in self.stop_words and len(w) > 1]
        return [w for w, _ in Counter(filtered).most_common(top_k)]

    def merge_and_deduplicate(self, *sources: list[str]) -> list[str]:
        """合并多源关键词并去重"""
        seen = set()
        result = []
        for source in sources:
            for kw in source:
                if kw not in seen and len(kw) >= 2:
                    seen.add(kw)
                    result.append(kw)
        return result
```

### 4.2.4 关键词评分器设计

**文件**: `MediaCrawler-Api/services/exploration/keyword_scorer.py`

```python
class KeywordScorer:
    """关键词评分器"""

    def __init__(self, seed_keywords: list[str], crawled_keywords: set[str]):
        self.seed_keywords = seed_keywords
        self.crawled_keywords = crawled_keywords

    def score(self, keyword: str, source_keyword: str,
              relation_type: str, cooccurrence_count: int,
              platform_estimated_total: int = 0) -> float:
        """
        评分 = w1*新颖度 + w2*关联度 + w3*信息增益 - w4*衰减
        """
        novelty = 1.0 if keyword not in self.crawled_keywords else 0.1
        relevance = self._calc_relevance(keyword, source_keyword)
        info_gain = min(platform_estimated_total / 1000, 1.0)
        decay = self._calc_distance_decay(source_keyword)

        return 0.35 * novelty + 0.35 * relevance + 0.20 * info_gain - 0.10 * decay

    def _calc_relevance(self, kw: str, source: str) -> float:
        """基于 jieba 分词的简单语义关联"""
        kw_words = set(jieba.cut(kw))
        source_words = set(jieba.cut(source))
        if not kw_words or not source_words:
            return 0.0
        intersection = kw_words & source_words
        return len(intersection) / max(len(kw_words), len(source_words))

    def _calc_distance_decay(self, source_keyword: str) -> float:
        """计算与种子词的距离衰减"""
        if source_keyword in self.seed_keywords:
            return 0.0
        return 0.3
```

### 4.2.5 探索调度器设计

**文件**: `MediaCrawler-Api/services/exploration/exploration_scheduler.py`

```python
class ExplorationScheduler:
    """自动化探索爬取调度器"""

    def __init__(self, task_id: int, config: dict):
        self.task_id = task_id
        self.seed_keywords = config.get("seed_keywords", [])
        self.max_depth = config.get("max_depth", 3)
        self.max_keywords_per_round = config.get("max_keywords_per_round", 5)
        self.current_round = 0
        self.keyword_queue = []  # (keyword, score) 优先级队列
        self.crawled_keywords = set()
        self.bloom_filter = BloomFilter(capacity=100000, error_rate=0.001)

    async def run(self):
        """主循环"""
        self.keyword_queue = [(kw, 1.0) for kw in self.seed_keywords]

        while self.keyword_queue and self.current_round < self.max_depth:
            self.current_round += 1

            # 按评分排序，取 TOP-K
            self.keyword_queue.sort(key=lambda x: -x[1])
            round_keywords = self.keyword_queue[:self.max_keywords_per_round]
            self.keyword_queue = self.keyword_queue[self.max_keywords_per_round:]

            # 逐关键词爬取
            for keyword, score in round_keywords:
                new_kws = await self._crawl_and_discover(keyword)

                # 新关键词入队
                for new_kw, new_score in new_kws:
                    if new_kw not in self.crawled_keywords:
                        self.keyword_queue.append((new_kw, new_score))

                self.crawled_keywords.add(keyword)

            # 持久化关键词关联图
            await self._persist_keyword_graph()
```

### 4.2.6 前端新增页面

**新增文件**: `MediaCrawler-Web/src/pages/Exploration/index.tsx`

```
ExplorationPage
  ├── PageHeader ("探索式爬取")
  ├── ExplorationCreateForm (种子关键词、最大深度、平台选择)
  ├── ExplorationStatusCard (当前轮次、已发现关键词、进度)
  ├── KeywordGraph (关键词关联图可视化 — 使用 ECharts 力导向图)
  └── ExplorationHistory (历史探索任务列表)
```

**路由新增**: `MediaCrawler-Web/src/router/index.tsx`
```typescript
{
  path: '/exploration',
  lazy: () => import('@/pages/Exploration'),
}
```

### 4.2.7 新增 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/exploration/start` | POST | 启动探索任务 |
| `/api/exploration/stop/{id}` | POST | 停止探索任务 |
| `/api/exploration/pause/{id}` | POST | 暂停探索任务 |
| `/api/exploration/resume/{id}` | POST | 恢复探索任务 |
| `/api/exploration/status/{id}` | GET | 获取探索进度 |
| `/api/exploration/keywords/{id}` | GET | 获取关键词列表及评分 |
| `/api/exploration/graph/{id}` | GET | 获取关键词关联图数据 |
| `/api/exploration/tasks` | GET | 探索任务历史列表 |

## 4.3 阶段三：数据清洗管道 — 技术实现

### 4.3.1 数据清洗器

**文件**: `MediaCrawler-Api/services/analysis/data_cleaner.py`

```python
import re
import html
from datetime import datetime

class DataCleaner:
    """基础数据清洗器 — 在 Store 层调用"""

    @staticmethod
    def clean_html(text: str | None) -> str | None:
        """去除 HTML 标签和特殊字符"""
        if not text:
            return None
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-z]+;', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def normalize_count(value) -> int | None:
        """将 '1.2w' / '12000' / '' 统一为整数"""
        if value is None or value == '' or value == 'null':
            return None
        if isinstance(value, (int, float)):
            return int(value)
        value = str(value).strip().lower()
        if 'w' in value:
            return int(float(value.replace('w', '')) * 10000)
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def normalize_timestamp(ts) -> int | None:
        """统一时间戳: 支持秒/毫秒/ISO格式"""
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            if ts < 1e10:  # 秒 → 毫秒
                return int(ts * 1000)
            return int(ts)
        if isinstance(ts, str):
            try:
                return int(datetime.fromisoformat(ts).timestamp() * 1000)
            except ValueError:
                return None
        return None

    @staticmethod
    def normalize_location(loc: str | None) -> str | None:
        """IP 属地标准化"""
        if not loc:
            return None
        loc = loc.strip().lstrip('来自').strip()
        location_map = {
            '上海': '上海市', '北京': '北京市', '天津': '天津市', '重庆': '重庆市',
        }
        return location_map.get(loc, loc)
```

### 4.3.2 情感分析器

**文件**: `MediaCrawler-Api/services/analysis/sentiment_analyzer.py`

```python
from snownlp import SnowNLP

class SentimentAnalyzer:
    """评论情感分析器"""

    def analyze(self, text: str) -> dict:
        """
        返回: {
            "sentiment": "positive"|"negative"|"neutral",
            "score": 0.0-1.0,  # 正面概率
            "confidence": 0.0-1.0
        }
        """
        if not text or len(text.strip()) < 2:
            return {"sentiment": "neutral", "score": 0.5, "confidence": 0.0}

        s = SnowNLP(text)
        score = s.sentiments  # 0-1, >0.5 正面

        if score > 0.7:
            sentiment = "positive"
        elif score < 0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        confidence = abs(score - 0.5) * 2  # 距离 0.5 越远越确定

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "confidence": round(confidence, 4)
        }

    async def batch_analyze(self, texts: list[str]) -> list[dict]:
        """批量分析"""
        return [self.analyze(t) for t in texts]
```

### 4.3.3 内容分类器

**文件**: `MediaCrawler-Api/services/analysis/content_classifier.py`

```python
class ContentClassifier:
    """内容自动分类器 — 基于关键词规则 + TF-IDF"""

    CATEGORY_RULES = {
        "教程": ["教程", "攻略", "方法", "技巧", "步骤", "指南", "入门", "学习"],
        "测评": ["测评", "评测", "体验", "开箱", "对比", "推荐", "值得买"],
        "Vlog": ["vlog", "日常", "生活", "记录", "一天", "周末"],
        "营销": ["广告", "合作", "赞助", "福利", "优惠", "折扣", "限时", "团购"],
        "资讯": ["消息", "发布", "官宣", "新闻", "公告", "上线", "更新"],
    }

    def classify(self, title: str, desc: str = "", tag_list: list[str] = None) -> dict:
        """返回: {"category": "教程", "confidence": 0.85}"""
        text = f"{title} {desc}"

        scores = {}
        for cat, keywords in self.CATEGORY_RULES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score

        if not scores:
            return {"category": "其他", "confidence": 0.3}

        best = max(scores, key=scores.get)
        total = sum(scores.values())

        return {
            "category": best,
            "confidence": round(scores[best] / total, 2)
        }
```

### 4.3.4 前端数据中心升级

**修改文件**: `MediaCrawler-Web/src/pages/Data/index.tsx`

在数据表格中增加新列：
- 情感标签列（正/负/中 彩色 Tag）
- 内容分类列
- 数据质量评分列

**新增组件**: `MediaCrawler-Web/src/pages/Data/components/SentimentFilter.tsx`
- 支持按情感类型筛选（正面/负面/中性）
- 情感分布统计图表

## 4.4 阶段四：风控增强 — 技术实现

### 4.4.1 频率监控器

**文件**: `MediaCrawler-Api/media_platform/rate_limiter.py` (新增)

```python
import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field

class RateLevel(Enum):
    NORMAL = "normal"
    SLOW = "slow"
    RECOVERY = "recovery"
    PAUSED = "paused"

@dataclass
class RateLimitMonitor:
    """请求频率监控器"""
    platform: str
    normal_interval: tuple[float, float]  # (min, max)
    slow_multiplier: float = 2.0
    recovery_threshold: int = 10  # 连续成功 N 次后恢复
    pause_duration: int = 300     # 暂停秒数

    current_level: RateLevel = RateLevel.NORMAL
    consecutive_success: int = 0
    consecutive_errors: int = 0
    error_types: list[str] = field(default_factory=list)

    def report_success(self):
        self.consecutive_success += 1
        self.consecutive_errors = 0
        if self.consecutive_success >= self.recovery_threshold:
            self._recover()

    def report_error(self, error_type: str):
        self.consecutive_errors += 1
        self.consecutive_success = 0
        self.error_types.append(error_type)

        if error_type in ("IPBlockError", "RateLimitError"):
            if self.consecutive_errors >= 3:
                self.current_level = RateLevel.PAUSED
            else:
                self.current_level = RateLevel.SLOW

    def get_sleep_interval(self) -> float:
        base_min, base_max = self.normal_interval
        if self.current_level == RateLevel.NORMAL:
            interval = base_min + (base_max - base_min) * (self.consecutive_success / 50)
        elif self.current_level == RateLevel.SLOW:
            interval = (base_min + (base_max - base_min) * 0.5) * self.slow_multiplier
        elif self.current_level == RateLevel.PAUSED:
            interval = self.pause_duration
        else:
            interval = base_min
        return min(interval, 300)

    def _recover(self):
        if self.current_level == RateLevel.SLOW:
            self.current_level = RateLevel.NORMAL
```

### 4.4.2 平台差异化配置表

**文件**: `MediaCrawler-Api/config/platform_risk_profiles.py` (新增)

```python
PLATFORM_RISK_PROFILES = {
    "xhs": {
        "risk_level": 5,
        "sleep_interval": (8, 20),
        "max_concurrency": 1,
        "max_notes": 100,
        "ua_type": "mobile",
        "require_cdp": True,
        "cookie_ttl_hours": 2,
    },
    "bili": {
        "risk_level": 3,
        "sleep_interval": (3, 10),
        "max_concurrency": 3,
        "max_notes": 300,
        "ua_type": "desktop",
        "require_cdp": False,
    },
    "tieba": {
        "risk_level": 2,
        "sleep_interval": (2, 6),
        "max_concurrency": 5,
        "max_notes": 500,
        "ua_type": "desktop",
        "require_cdp": False,
    },
}
```

## 4.5 阶段五：商业分析层 — 技术实现

### 4.5.1 分析 API 设计

```
/api/analytics/
  ├── GET  /dashboard/overview        概览数据
  │    参数: platform?, date_range?
  │    返回: {total_contents, total_comments, platforms_breakdown, daily_trend}
  │
  ├── GET  /dashboard/trends          趋势数据
  │    参数: platform, keyword?, days=30
  │    返回: [{date, count, avg_likes, avg_comments}, ...]
  │
  ├── GET  /topics/hot                热门话题
  │    参数: platform, days=7, limit=20
  │    返回: [{keyword, count, engagement_score}, ...]
  │
  ├── GET  /topics/sentiment          话题情感分析
  │    参数: platform, keyword
  │    返回: {positive_ratio, negative_ratio, neutral_ratio, trend: [...]}
  │
  ├── GET  /creators/ranking          创作者榜单
  │    参数: platform, sort_by=influence, limit=50
  │    返回: [{user_id, nickname, followers, engagement_rate, ...}, ...]
  │
  ├── GET  /creators/{id}/profile     创作者画像
  │    参数: user_id
  │    返回: {basic_info, content_stats, growth_curve, top_contents}
  │
  ├── GET  /content/top               热门内容
  │    参数: platform, keyword?, sort_by=likes, limit=20
  │    返回: [{note_id, title, likes, comments, sentiment}, ...]
  │
  ├── GET  /compare/creators          创作者对比
  │    参数: creator_ids[] (2-5个)
  │    返回: {radar_chart_data, bar_chart_data, table_data}
  │
  └── POST /reports/generate          生成报告
       参数: {platform, keyword?, date_range, format: pdf|md}
       返回: {report_id, download_url}
```

### 4.5.2 前端看板重构

```
Dashboard (重新设计)
  ├── Row 1: 4 个 MetricCard (复用现有)
  ├── Row 2: 趋势折线图 (ECharts) — 近 30 天数据量变化
  ├── Row 3: 平台分布饼图 (ECharts) + 情感分布柱状图
  ├── Row 4: 热门关键词词云 (ECharts wordCloud)
  └── Row 5: 最近任务列表 (复用现有)

话题分析页 (新增)
  ├── 关键词搜索 → 话题详情
  ├── 情感趋势折线图
  ├── 内容分类树图
  ├── 热门内容列表
  └── 关联话题推荐 (基于 keyword_graph)

创作者分析页 (新增)
  ├── 创作者搜索 → 详情
  ├── 影响力评分雷达图
  ├── 粉丝增长曲线
  ├── 热门内容列表
  └── 同类创作者推荐
```

### 4.5.3 报告生成器

**文件**: `MediaCrawler-Api/services/report_generator.py` (新增)

```python
class ReportGenerator:
    """分析报告生成器"""

    async def generate(self, params: ReportParams) -> str:
        """生成 Markdown 报告，返回文件路径"""
        data = await self._collect_data(params)

        report = f"""# {params.keyword or params.platform} 数据分析报告
> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据范围: {params.date_range}

## 一、数据概览
- 总内容数: {data['total_contents']}
- 总评论数: {data['total_comments']}
- 覆盖平台: {data['platforms']}

## 二、趋势分析
{self._generate_trend_chart_description(data['trends'])}

## 三、情感分析
- 正面评论占比: {data['sentiment']['positive_ratio']:.1%}
- 负面评论占比: {data['sentiment']['negative_ratio']:.1%}
- 中性评论占比: {data['sentiment']['neutral_ratio']:.1%}

## 四、热门内容 TOP 10
{self._generate_top_content_table(data['top_contents'])}

## 五、创作者榜单
{self._generate_creator_table(data['top_creators'])}
"""
        return report
```

---

# 五、测试方案

## 5.1 测试策略概览

```
测试金字塔:
         ┌──────┐
         │ E2E  │  ← 浏览器 MCP 端到端测试
         ├──────┤
         │ 集成  │  ← API 集成测试 + DB 测试
         ├──────┤
         │ 单元  │  ← 服务层 / 工具函数测试
         └──────┘
```

## 5.2 阶段一测试

### 5.2.1 单元测试

| 测试项 | 文件 | 验证点 |
|--------|------|--------|
| UNIQUE 约束生效 | `tests/test_db_unique.py` | 插入重复 note_id 抛出 IntegrityError |
| 默认配置值 | `tests/test_config_defaults.py` | CRAWLER_MAX_NOTES_COUNT >= 100 |
| 随机间隔生成 | `tests/test_sleep_interval.py` | 生成的间隔在 [min, max] 范围内 |
| 进度追踪 | `tests/test_progress_tracker.py` | completed 数递增正确 |

### 5.2.2 集成测试

| 测试项 | 验证点 |
|--------|--------|
| 爬取 50 条小红书笔记 | 去重后实际写入 50 条，无重复 |
| 配置方案创建 | 新建方案的 max_notes 默认值为 100 |
| 前端配置表单 | 输入框默认值显示 100 |

### 5.2.3 冒烟测试

- 启动后端服务 → 访问 `/api/health` 返回 ok
- 启动前端 → 访问首页 → 概览正常显示
- 新建配置方案 → 保存 → 列表显示
- 启动爬虫任务 → 完成 → 数据中心可查询到数据

## 5.3 阶段二测试

### 5.3.1 关键词提取测试

| 测试项 | 输入 | 期望输出 |
|--------|------|---------|
| tag_list 提取 | `'["Python","远程工作","程序员"]'` | `["Python","远程工作","程序员"]` |
| 标题 TF-IDF | "零基础Python副业月入过万经验" | 包含"Python""副业" |
| 评论高频词 | ["这个教程很好","教程很详细"] | "教程"排在前面 |
| 空输入处理 | `tag_list=""` | 返回空列表 |
| 异常 JSON | `tag_list="{invalid}"` | 返回空列表不崩溃 |

### 5.3.2 评分器测试

| 测试项 | 验证点 |
|--------|--------|
| 未爬取词新颖度 | `novelty = 1.0` |
| 已爬取词新颖度 | `novelty = 0.1` |
| 相同词的关联度 | `relevance ≈ 1.0` |
| 不相关词的关联度 | `relevance ≈ 0.0` |
| 种子词衰减 | `decay = 0.0` |
| 非种子词衰减 | `decay > 0.0` |

### 5.3.3 探索调度器集成测试

| 测试项 | 验证点 |
|--------|--------|
| 正常流程 | 种子词 → 发现新词 → 爬取新词 → 直到深度上限 |
| 关键词爆炸控制 | max_keywords_per_round=5 时每轮不超过 5 个 |
| 深度上限控制 | max_depth=3 时最多 3 轮 |
| 暂停/恢复 | 暂停后状态不变，恢复后继续 |
| 去重有效性 | Bloom Filter 正确拦截已爬 note_id |

### 5.3.4 前端 E2E 测试（浏览器 MCP）

| 测试项 | 操作步骤 |
|--------|---------|
| 创建探索任务 | 导航到探索页 → 输入种子关键词 → 选择平台 → 设置深度 → 点击启动 |
| 查看探索进度 | 观察进度条更新 → 查看已发现关键词列表 |
| 暂停/恢复/停止 | 点击暂停 → 确认暂停 → 点击恢复 → 确认恢复 |
| 关键词图可视化 | 检查力导向图是否正确渲染节点和边 |

## 5.4 阶段三测试

### 5.4.1 数据清洗测试

| 测试项 | 输入 | 期望输出 |
|--------|------|---------|
| HTML 清理 | `"标题<br/>内容&nbsp;文本"` | `"标题内容 文本"` |
| 计数标准化 | `"1.2w"` | `12000` |
| 计数标准化 | `""` | `None` |
| 时间戳标准化(秒) | `1715900000` | `1715900000000` |
| 时间戳标准化(毫秒) | `1715900000000` | `1715900000000` |
| IP 标准化 | `"来自上海"` | `"上海市"` |
| 空文本 | `None` | `None` |

### 5.4.2 情感分析测试

| 测试项 | 输入 | 期望 |
|--------|------|------|
| 明显正面 | "这个产品太好用了，强烈推荐！" | sentiment=positive, score>0.7 |
| 明显负面 | "垃圾产品，浪费钱，千万别买" | sentiment=negative, score<0.3 |
| 中性 | "产品收到了，还没用" | sentiment=neutral |
| 空文本 | "" | sentiment=neutral, confidence=0.0 |

### 5.4.3 内容分类测试

| 测试项 | 输入 | 期望 |
|--------|------|------|
| 教程类 | "Python入门教程：30天从零到大神" | category=教程 |
| 测评类 | "iPhone 16 Pro 深度评测 | 值得买吗？" | category=测评 |
| 营销类 | "限时优惠！全场5折起 快抢" | category=营销 |

## 5.5 阶段四测试

### 5.5.1 频率监控测试

| 测试项 | 验证点 |
|--------|--------|
| 正常模式 | 连续成功后间隔按配置执行 |
| 降速模式 | 3 次 RateLimitError 后间隔翻倍 |
| 恢复模式 | 连续 10 次成功后恢复正常间隔 |
| 暂停模式 | IPBlockError 后暂停 5 分钟 |

### 5.5.2 UA 轮换测试

| 测试项 | 验证点 |
|--------|--------|
| 连续 10 次请求 | UA 不重复 |
| 平台适配 | 小红书用移动端 UA，B站用桌面端 UA |

## 5.6 阶段五测试

### 5.6.1 看板数据测试

| 测试项 | 验证点 |
|--------|--------|
| 趋势查询 | 返回 30 天内每天的数据点 |
| 热门话题 | 按互动量降序排列 |
| 创作者榜单 | 按影响力评分降序排列 |
| 报告生成 | 生成的 Markdown 格式正确 |

### 5.6.2 前端组件测试

| 组件 | 验证点 |
|------|--------|
| MetricCard | 4 种状态正确渲染 |
| 趋势折线图 | 数据点正确映射 |
| 词云 | 关键词和频次正确 |
| 情感分布图 | 正/负/中比例正确 |

## 5.7 回归测试清单（每次发布前执行）

- [ ] 所有平台基本爬取流程正常（搜索/详情/创作者三种模式）
- [ ] CDP 模式正常工作
- [ ] IP 代理正常切换
- [ ] 登录流程正常（二维码/手机号/Cookie）
- [ ] 数据库写入和查询正常
- [ ] WebSocket 日志推送正常
- [ ] 前端 4 个页面正常加载
- [ ] 配置方案 CRUD 正常
- [ ] 任务历史查询正常

---

# 六、验收方案

## 6.1 阶段一验收标准

| # | 验收项 | 验收标准 | 验收方式 |
|---|--------|---------|---------|
| 1.1 | 默认数据量 | `CRAWLER_MAX_NOTES_COUNT` 默认值 ≥ 100 | 查看配置文件 + 新建方案验证 |
| 1.2 | 默认评论量 | `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES` 默认值 ≥ 30 | 同上 |
| 1.3 | 数据库 UNIQUE 约束 | 所有内容/评论表的核心 ID 字段有 UNIQUE 约束 | SQL: `SHOW INDEX FROM xhs_note WHERE Key_name LIKE 'uk_%'` |
| 1.4 | 重复数据拦截 | 插入相同 note_id 抛异常 | 单元测试 |
| 1.5 | 前端默认值 | 新建方案表单中 max_notes 默认显示 100 | 浏览器操作验证 |
| 1.6 | 任务进度显示 | 运行中的任务显示进度信息（已爬数/总数） | WebSocket + 前端状态栏 |

## 6.2 阶段二验收标准

| # | 验收项 | 验收标准 | 验收方式 |
|---|--------|---------|---------|
| 2.1 | 标签关键词提取 | 含 tag_list 的笔记爬取后自动提取标签 | 查看 keyword_graph 表 |
| 2.2 | 文本关键词提取 | title+desc 的 TF-IDF 提取正确 | 单元测试 |
| 2.3 | 评论关键词提取 | 评论高频词提取正确 | 单元测试 |
| 2.4 | 关键词评分 | 新颖度+关联度+信息增益评分合理 | 对比人工判断 |
| 2.5 | 探索调度 | 种子词→发现→爬取→再发现 自动循环 | 端到端测试 |
| 2.6 | 深度控制 | 达到 max_depth 后自动停止 | 查看 exploration_task 表 |
| 2.7 | 关键词数量控制 | 每轮新关键词 ≤ max_keywords_per_round | 查看调度日志 |
| 2.8 | 暂停/恢复 | 暂停后状态持久化，恢复后继续 | 浏览器操作验证 |
| 2.9 | 去重有效性 | 重复 note_id 被 Bloom Filter 拦截 | 日志统计 |
| 2.10 | 前端探索页 | 探索任务创建/监控/停止/关键词图 完整可用 | 浏览器 MCP 测试 |

## 6.3 阶段三验收标准

| # | 验收项 | 验收标准 | 验收方式 |
|---|--------|---------|---------|
| 3.1 | HTML 清理 | 所有写入数据库的文本字段无 HTML 标签 | 查询抽查 |
| 3.2 | 计数标准化 | liked_count 字段为纯整数（非 '1.2w' 格式） | 查询抽查 |
| 3.3 | 时间戳统一 | 所有时间字段为毫秒级 Unix timestamp | 查询抽查 |
| 3.4 | 空值统一 | 空字符串/0/null 统一为 NULL | 查询抽查 |
| 3.5 | IP 标准化 | "来自上海"→"上海市" | 查询抽查 |
| 3.6 | 情感分析 | 评论正/负/中性分类准确率 ≥ 70% | 抽样 100 条人工验证 |
| 3.7 | 内容分类 | 分类准确率 ≥ 75% | 抽样 100 条人工验证 |
| 3.8 | 前端情感显示 | 数据表情感列彩色 Tag 正确显示 | 浏览器操作验证 |
| 3.9 | 前端分类筛选 | 按分类筛选正确过滤 | 浏览器操作验证 |

## 6.4 阶段四验收标准

| # | 验收项 | 验收标准 | 验收方式 |
|---|--------|---------|---------|
| 4.1 | 频控降速 | 连续 3 次限流错误后间隔翻倍 | 模拟限流测试 |
| 4.2 | 频控恢复 | 连续 10 次成功后恢复正常间隔 | 模拟恢复测试 |
| 4.3 | UA 轮换 | 每次请求 UA 不重复 | HTTP 抓包验证 |
| 4.4 | 平台差异化 | 小红书间隔范围 [8,20]s，贴吧 [2,6]s | 日志验证 |
| 4.5 | 代理评分 | 低成功率代理被淘汰 | 代理池日志 |

## 6.5 阶段五验收标准

| # | 验收项 | 验收标准 | 验收方式 |
|---|--------|---------|---------|
| 5.1 | 概览看板 | 4 个 MetricCard + 趋势图 + 平台分布图 + 词云 | 浏览器操作验证 |
| 5.2 | 话题分析 | 输入关键词可查看趋势/情感/分类 | 浏览器操作验证 |
| 5.3 | 创作者榜单 | 按影响力排序展示 | 浏览器操作验证 |
| 5.4 | 报告生成 | 可导出含数据概览/趋势/情感/排行榜的 Markdown | 下载文件验证 |
| 5.5 | 竞品对比 | 2-5 个创作者对比雷达图 | 浏览器操作验证 |
| 5.6 | 响应时间 | 看板加载 ≤ 3 秒 | 性能测试 |
| 5.7 | 数据准确 | 看板数据与数据库查询结果一致 | SQL 对比验证 |

---

# 附录 A：完整文件变更清单

## A.1 后端新增文件

| 文件 | 用途 |
|------|------|
| `MediaCrawler-Api/services/exploration/__init__.py` | 探索模块导出 |
| `MediaCrawler-Api/services/exploration/keyword_extractor.py` | 多源关键词提取器 |
| `MediaCrawler-Api/services/exploration/keyword_scorer.py` | 关键词评分器 |
| `MediaCrawler-Api/services/exploration/exploration_scheduler.py` | 探索调度器 |
| `MediaCrawler-Api/services/exploration/bloom_filter.py` | Bloom Filter 实现 |
| `MediaCrawler-Api/services/analysis/__init__.py` | 分析模块导出 |
| `MediaCrawler-Api/services/analysis/data_cleaner.py` | 数据清洗器 |
| `MediaCrawler-Api/services/analysis/sentiment_analyzer.py` | 情感分析器 |
| `MediaCrawler-Api/services/analysis/content_classifier.py` | 内容分类器 |
| `MediaCrawler-Api/services/report_generator.py` | 报告生成器 |
| `MediaCrawler-Api/media_platform/rate_limiter.py` | 频率监控器 |
| `MediaCrawler-Api/config/platform_risk_profiles.py` | 平台风控配置 |
| `MediaCrawler-Api/api/routers/exploration.py` | 探索式爬取 API |
| `MediaCrawler-Api/api/routers/analytics.py` | 分析 API |
| `MediaCrawler-Api/api/schemas/exploration.py` | 探索相关 Pydantic 模型 |
| `MediaCrawler-Api/api/schemas/analytics.py` | 分析相关 Pydantic 模型 |

## A.2 后端修改文件

| 文件 | 变更内容 |
|------|---------|
| `config/base_config.py` | 提高默认值，增加 sleep_max 配置 |
| `config/profile_defaults.py` | 同步默认值 |
| `database/models.py` | 增加 UNIQUE 约束 |
| `database/system_models.py` | 新增 keyword_graph 和 exploration_task 模型 |
| `store/xhs/_store_impl.py` | 改为 ON DUPLICATE KEY UPDATE |
| `store/douyin/_store_impl.py` | 同上 |
| `store/bilibili/_store_impl.py` | 同上 |
| `store/weibo/_store_impl.py` | 同上 |
| `store/kuaishou/_store_impl.py` | 同上 |
| `store/tieba/_store_impl.py` | 同上 |
| `store/zhihu/_store_impl.py` | 同上 |
| `api/main.py` | 注册新路由 |
| `api/schemas/crawler.py` | 新增 CrawlerProgress 模型 |
| `media_platform/xhs/core.py` | 集成频率监控 + 进度追踪 |
| `media_platform/bilibili/core.py` | 同上 |
| `media_platform/douyin/core.py` | 同上 |
| `media_platform/weibo/core.py` | 同上 |
| `media_platform/kuaishou/core.py` | 同上 |
| `media_platform/tieba/core.py` | 同上 |
| `media_platform/zhihu/core.py` | 同上 |
| `services/data_query_service.py` | 增加分析查询方法 |

## A.3 前端新增文件

| 文件 | 用途 |
|------|------|
| `src/pages/Exploration/index.tsx` | 探索式爬取页面 |
| `src/pages/Exploration/components/ExplorationCreateForm.tsx` | 探索任务创建表单 |
| `src/pages/Exploration/components/ExplorationStatusCard.tsx` | 探索进度卡片 |
| `src/pages/Exploration/components/KeywordGraph.tsx` | ECharts 关键词关联图 |
| `src/pages/Topics/index.tsx` | 话题分析页 |
| `src/pages/Creators/index.tsx` | 创作者分析页 |
| `src/pages/Dashboard/components/TrendChart.tsx` | 趋势折线图 |
| `src/pages/Dashboard/components/PlatformPieChart.tsx` | 平台分布饼图 |
| `src/pages/Dashboard/components/SentimentBar.tsx` | 情感分布柱状图 |
| `src/pages/Dashboard/components/HotWordCloud.tsx` | 热门关键词词云 |
| `src/pages/Data/components/SentimentFilter.tsx` | 情感筛选器 |

## A.4 前端修改文件

| 文件 | 变更内容 |
|------|---------|
| `src/types/config.ts` | 更新 DEFAULT_PAYLOAD |
| `src/types/api.ts` | 新增分析相关类型 |
| `src/router/index.tsx` | 新增探索/话题/创作者路由 |
| `src/pages/Dashboard/index.tsx` | 重构为分析看板 |
| `src/pages/Settings/index.tsx` | 增加平台风控设置 Tab |
| `src/pages/Data/index.tsx` | 增加情感/分类列 |
| `src/constants/fields.ts` | 新增情感和分类字段映射 |
| `src/api/modules/exploration.ts` | 探索 API 模块 |
| `src/api/modules/analytics.ts` | 分析 API 模块 |
| `src/layouts/BasicLayout/index.tsx` | 菜单增加探索/话题/创作者入口 |

---

# 附录 B：技术风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 小红书 API 签名算法变更 | 爬虫失效 | 中 | HTML 解析 fallback + 关注社区 |
| MySQL UNIQUE 约束导致历史重复数据迁移失败 | 上线阻塞 | 高 | 先去重再添加约束，预执行 dry-run |
| snownlp 情感分析准确度低 | 分析结论不可信 | 中 | 提供置信度分数，低置信度标注"不确定" |
| 探索式爬取触发风控 | 账号被封 | 高 | 保守的间隔配置 + 频率监控 + 多账号 |
| 关键词数量爆炸 | 系统资源耗尽 | 中 | max_keywords_per_round + total_keywords_limit |
| ECharts 大数据量渲染慢 | 前端卡顿 | 低 | 数据聚合后再渲染 + 虚拟滚动 |
| WebSocket 连接数过多 | 后端压力 | 低 | 限制最大连接数 + 定期清理死连接 |
| MySQL 数据量过大查询慢 | API 响应慢 | 中 | 索引优化 + 分区表 + 定期归档 |

---

# 附录 C：里程碑与交付时间线

```
Week 1-2:  阶段一 数据量杠杆
  Day 1-3: 配置修改 + 数据库 UNIQUE 约束
  Day 4-6: 前端表单更新 + 进度追踪
  Day 7-8: 测试 + 修复
  Day 9-10: 验收 + 发布 v2.1

Week 3-7:  阶段二 探索式爬取 (最复杂)
  Week 3: 关键词提取器 + 评分器
  Week 4: 探索调度器 + Bloom Filter
  Week 5: API 端点 + 前端页面
  Week 6: 集成测试 + E2E 测试
  Week 7: 修复 + 验收 + 发布 v2.2

Week 8-10: 阶段三 数据清洗管道
  Week 8: 数据清洗器 + 情感分析器 + 内容分类器
  Week 9: API 集成 + 前端展示
  Week 10: 测试 + 验收 + 发布 v2.3

Week 11-13: 阶段四 风控增强
  Week 11: 频率监控器 + 平台差异化配置
  Week 12: UA 轮换 + 代理评分
  Week 13: 测试 + 验收 + 发布 v2.4

Week 14-20: 阶段五 商业分析层
  Week 14-15: 分析 API 开发
  Week 16-17: 前端看板重构 + 新增页面
  Week 18: 报告生成器
  Week 19: 全面测试
  Week 20: 验收 + 发布 v3.0
```
