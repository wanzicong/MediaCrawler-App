# -*- coding: utf-8 -*-
"""关键词管理与 AI 裂变路由"""
import json
import os
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func

from database.db_session import get_mysql_session
from database.system_models import KeywordGroup, Keyword

router = APIRouter(prefix="/keywords", tags=["keywords"])

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


# ── Helpers ──────────────────────────────────────────────────────────

def _get_api_key() -> str:
    from pathlib import Path
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    return os.getenv("DEEPSEEK_API_KEY", "")


def _format_dt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


# ── Pydantic Models ─────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = ""
    color: Optional[str] = "#6366f1"
    sort_order: Optional[int] = 0


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: str
    color: str
    sort_order: int
    keyword_count: int = 0
    created_at: str
    updated_at: str


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=256)
    group_id: Optional[int] = None
    platform: Optional[str] = "xhs"
    source: Optional[str] = "manual"
    notes: Optional[str] = ""


class KeywordBatchCreate(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=500)
    group_id: Optional[int] = None
    platform: Optional[str] = "xhs"


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = Field(None, max_length=256)
    group_id: Optional[int] = None
    platform: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    crawled_count: Optional[int] = None
    results_count: Optional[int] = None
    notes: Optional[str] = None


class KeywordOut(BaseModel):
    id: int
    group_id: Optional[int]
    keyword: str
    platform: str
    source: str
    status: str
    crawled_count: int
    results_count: int
    notes: str
    created_at: str
    updated_at: str


class KeywordListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[KeywordOut]


class BatchDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class FissionRequest(BaseModel):
    seed_keyword: str = Field(..., min_length=1, max_length=128)
    platform: Optional[str] = "xhs"
    platforms: Optional[list[str]] = []
    depth: Optional[int] = Field(1, ge=1, le=2)


class FissionItem(BaseModel):
    keyword: str
    platform: str
    category: str
    reason: str


class FissionResponse(BaseModel):
    seed_keyword: str
    platforms: list[str]
    generated: list[FissionItem]


class StatsByGroup(BaseModel):
    group_name: str
    count: int


class StatsByStatus(BaseModel):
    status: str
    count: int


class TopPerforming(BaseModel):
    keyword: str
    results_count: int
    crawled_count: int


class StatsResponse(BaseModel):
    total_keywords: int
    by_group: list[StatsByGroup]
    by_status: list[StatsByStatus]
    top_performing: list[TopPerforming]


# ── 自动记录 & AI 分类 模型 ──────────────────────────────────────────

class AutoRecordRequest(BaseModel):
    """爬虫任务关键词自动记录请求"""
    platform: str = Field(..., min_length=1, max_length=32)
    keywords: str = Field(..., min_length=1, description="逗号分隔的关键词字符串")
    task_id: Optional[int] = None


class AutoRecordItem(BaseModel):
    keyword_id: int
    keyword: str
    platform: str
    action: str  # "created" 或 "updated"


class AutoRecordResponse(BaseModel):
    total: int
    created: int
    updated: int
    items: list[AutoRecordItem]


class AutoClassifyRequest(BaseModel):
    """AI 自动分类请求"""
    keyword_id: Optional[int] = None
    keyword: Optional[str] = Field(None, min_length=1, max_length=256)


class AutoClassifyResponse(BaseModel):
    """AI 自动分类结果"""
    keyword_id: int
    keyword: str
    group_name: str
    group_id: int
    group_created: bool  # 是否自动创建了新分组


class AutoClassifyBatchRequest(BaseModel):
    """批量 AI 自动分类请求"""
    keyword_ids: list[int] = Field(..., min_length=1, max_length=200)


class AutoClassifyBatchResponse(BaseModel):
    total: int
    classified: int
    failed: int
    results: list[AutoClassifyResponse]


# ── Keyword Group Endpoints ─────────────────────────────────────────

@router.post("/groups", response_model=GroupOut)
async def create_group(body: GroupCreate):
    async with get_mysql_session() as session:
        # Check uniqueness
        existing = await session.execute(
            select(KeywordGroup).where(KeywordGroup.name == body.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"分组名称 '{body.name}' 已存在")

        group = KeywordGroup(
            name=body.name,
            description=body.description or "",
            color=body.color or "#6366f1",
            sort_order=body.sort_order or 0,
        )
        session.add(group)
        await session.flush()
        await session.commit()

        return GroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            sort_order=group.sort_order,
            keyword_count=0,
            created_at=_format_dt(group.created_at),
            updated_at=_format_dt(group.updated_at),
        )


@router.get("/groups", response_model=list[GroupOut])
async def list_groups():
    async with get_mysql_session() as session:
        # Get all groups
        result = await session.execute(
            select(KeywordGroup).order_by(KeywordGroup.sort_order, KeywordGroup.id)
        )
        groups = result.scalars().all()

        # Get keyword counts per group
        count_result = await session.execute(
            select(Keyword.group_id, func.count(Keyword.id))
            .where(Keyword.group_id.isnot(None))
            .group_by(Keyword.group_id)
        )
        count_map = {row[0]: row[1] for row in count_result.all()}

        return [
            GroupOut(
                id=g.id,
                name=g.name,
                description=g.description or "",
                color=g.color or "#6366f1",
                sort_order=g.sort_order or 0,
                keyword_count=count_map.get(g.id, 0),
                created_at=_format_dt(g.created_at),
                updated_at=_format_dt(g.updated_at),
            )
            for g in groups
        ]


@router.put("/groups/{group_id}", response_model=GroupOut)
async def update_group(group_id: int, body: GroupUpdate):
    async with get_mysql_session() as session:
        group = await session.get(KeywordGroup, group_id)
        if not group:
            raise HTTPException(404, "分组不存在")

        if body.name is not None:
            # Check uniqueness if name changed
            existing = await session.execute(
                select(KeywordGroup).where(
                    KeywordGroup.name == body.name, KeywordGroup.id != group_id
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(400, f"分组名称 '{body.name}' 已存在")
            group.name = body.name
        if body.description is not None:
            group.description = body.description
        if body.color is not None:
            group.color = body.color
        if body.sort_order is not None:
            group.sort_order = body.sort_order

        group.updated_at = datetime.utcnow()
        await session.commit()

        # Get keyword count
        count_result = await session.execute(
            select(func.count(Keyword.id)).where(Keyword.group_id == group_id)
        )
        kw_count = count_result.scalar() or 0

        return GroupOut(
            id=group.id,
            name=group.name,
            description=group.description or "",
            color=group.color or "#6366f1",
            sort_order=group.sort_order or 0,
            keyword_count=kw_count,
            created_at=_format_dt(group.created_at),
            updated_at=_format_dt(group.updated_at),
        )


@router.delete("/groups/{group_id}")
async def delete_group(group_id: int):
    async with get_mysql_session() as session:
        group = await session.get(KeywordGroup, group_id)
        if not group:
            raise HTTPException(404, "分组不存在")

        # Cascade delete all keywords in this group
        await session.execute(
            delete(Keyword).where(Keyword.group_id == group_id)
        )
        await session.delete(group)
        await session.commit()
        return {"status": "ok", "deleted_group_id": group_id}


# ── Keyword Endpoints ───────────────────────────────────────────────

@router.post("", response_model=KeywordOut)
async def create_keyword(
    body: KeywordCreate,
    auto_classify: bool = Query(False, description="创建后自动 AI 分类"),
):
    async with get_mysql_session() as session:
        if body.group_id is not None:
            group = await session.get(KeywordGroup, body.group_id)
            if not group:
                raise HTTPException(404, "分组不存在")

        kw = Keyword(
            keyword=body.keyword.strip(),
            group_id=body.group_id,
            platform=body.platform or "xhs",
            source=body.source or "manual",
            notes=body.notes or "",
        )
        session.add(kw)
        await session.flush()
        await session.commit()

        # 自动 AI 分类（不阻塞主流程）
        classified_group_id = kw.group_id
        if auto_classify and not kw.group_id:
            try:
                api_key = _get_api_key()
                if api_key:
                    groups_result = await session.execute(
                        select(KeywordGroup).order_by(KeywordGroup.sort_order, KeywordGroup.id)
                    )
                    groups = groups_result.scalars().all()
                    groups_list = [
                        {"id": g.id, "name": g.name, "description": g.description or ""}
                        for g in groups
                    ]
                    classify_result = await _do_classify_keyword(kw, api_key, groups_list)
                    classified_group_id = classify_result.group_id
            except Exception:
                pass  # AI 分类失败不影响关键词创建

        return KeywordOut(
            id=kw.id,
            group_id=classified_group_id,
            keyword=kw.keyword,
            platform=kw.platform,
            source=kw.source,
            status=kw.status,
            crawled_count=kw.crawled_count or 0,
            results_count=kw.results_count or 0,
            notes=kw.notes or "",
            created_at=_format_dt(kw.created_at),
            updated_at=_format_dt(kw.updated_at),
        )


@router.post("/batch", response_model=list[KeywordOut])
async def batch_create_keywords(body: KeywordBatchCreate):
    if not body.keywords:
        raise HTTPException(400, "关键词列表不能为空")
    if len(body.keywords) > 500:
        raise HTTPException(400, "单次最多添加 500 个关键词")

    async with get_mysql_session() as session:
        if body.group_id is not None:
            group = await session.get(KeywordGroup, body.group_id)
            if not group:
                raise HTTPException(404, "分组不存在")

        created: list[KeywordOut] = []
        for kw_text in body.keywords:
            kw_text = kw_text.strip()
            if not kw_text:
                continue
            kw = Keyword(
                keyword=kw_text,
                group_id=body.group_id,
                platform=body.platform or "xhs",
                source="manual",
            )
            session.add(kw)
            await session.flush()
            created.append(KeywordOut(
                id=kw.id,
                group_id=kw.group_id,
                keyword=kw.keyword,
                platform=kw.platform,
                source=kw.source,
                status=kw.status,
                crawled_count=kw.crawled_count or 0,
                results_count=kw.results_count or 0,
                notes=kw.notes or "",
                created_at=_format_dt(kw.created_at),
                updated_at=_format_dt(kw.updated_at),
            ))

        await session.commit()
        return created


# ── 自动记录 & AI 分类关键词 ───────────────────────────────────────

@router.post("/auto-record", response_model=AutoRecordResponse)
async def auto_record_keywords(body: AutoRecordRequest):
    """内部 API: Crawler-Service 启动爬虫时，自动同步关键词到词库"""
    keyword_list = [kw.strip() for kw in body.keywords.split(",") if kw.strip()]
    if not keyword_list:
        return AutoRecordResponse(total=0, created=0, updated=0, items=[])

    created_count = 0
    updated_count = 0
    items: list[AutoRecordItem] = []

    async with get_mysql_session() as session:
        for kw_text in keyword_list:
            result = await session.execute(
                select(Keyword).where(
                    Keyword.keyword == kw_text,
                    Keyword.platform == body.platform,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.crawled_count = (existing.crawled_count or 0) + 1
                existing.updated_at = datetime.utcnow()
                updated_count += 1
                items.append(AutoRecordItem(
                    keyword_id=existing.id,
                    keyword=existing.keyword,
                    platform=existing.platform,
                    action="updated",
                ))
            else:
                kw = Keyword(
                    keyword=kw_text,
                    platform=body.platform,
                    source="crawler",
                )
                session.add(kw)
                await session.flush()
                created_count += 1
                items.append(AutoRecordItem(
                    keyword_id=kw.id,
                    keyword=kw.keyword,
                    platform=kw.platform,
                    action="created",
                ))

        await session.commit()

    return AutoRecordResponse(
        total=len(keyword_list),
        created=created_count,
        updated=updated_count,
        items=items,
    )


@router.post("/auto-classify", response_model=AutoClassifyResponse)
async def auto_classify_keyword(body: AutoClassifyRequest):
    """AI 自动分类关键词: 调用 DeepSeek 判断关键词所属分组，分组不存在则自动创建"""
    async with get_mysql_session() as session:
        if body.keyword_id:
            kw = await session.get(Keyword, body.keyword_id)
            if not kw:
                raise HTTPException(404, "关键词不存在")
        elif body.keyword:
            result = await session.execute(
                select(Keyword).where(Keyword.keyword == body.keyword.strip())
            )
            kw = result.scalar_one_or_none()
            if not kw:
                raise HTTPException(404, f"关键词 '{body.keyword}' 不存在")
        else:
            raise HTTPException(400, "请提供 keyword_id 或 keyword")

        groups_result = await session.execute(
            select(KeywordGroup).order_by(KeywordGroup.sort_order, KeywordGroup.id)
        )
        groups = groups_result.scalars().all()
        groups_list = [
            {"id": g.id, "name": g.name, "description": g.description or ""}
            for g in groups
        ]

    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    try:
        return await _do_classify_keyword(kw, api_key, groups_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI 自动分类失败: {str(e)}")


@router.post("/auto-classify/batch", response_model=AutoClassifyBatchResponse)
async def batch_auto_classify(body: AutoClassifyBatchRequest):
    """批量 AI 自动分类: 对未分组关键词逐个分类，单个失败不影响其他"""
    async with get_mysql_session() as session:
        result = await session.execute(
            select(Keyword).where(
                Keyword.id.in_(body.keyword_ids),
                Keyword.group_id.is_(None),
            )
        )
        keywords = result.scalars().all()

    if not keywords:
        return AutoClassifyBatchResponse(total=0, classified=0, failed=0, results=[])

    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    async with get_mysql_session() as session:
        groups_result = await session.execute(
            select(KeywordGroup).order_by(KeywordGroup.sort_order, KeywordGroup.id)
        )
        groups = groups_result.scalars().all()
        groups_list = [
            {"id": g.id, "name": g.name, "description": g.description or ""}
            for g in groups
        ]

    classified = 0
    failed = 0
    results: list[AutoClassifyResponse] = []

    for kw in keywords:
        try:
            classify_result = await _do_classify_keyword(kw, api_key, groups_list)
            results.append(classify_result)
            classified += 1
        except Exception:
            failed += 1
            results.append(AutoClassifyResponse(
                keyword_id=kw.id,
                keyword=kw.keyword,
                group_name="",
                group_id=0,
                group_created=False,
            ))

    return AutoClassifyBatchResponse(
        total=len(keywords),
        classified=classified,
        failed=failed,
        results=results,
    )


@router.get("", response_model=KeywordListOut)
async def list_keywords(
    group_id: Optional[int] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    async with get_mysql_session() as session:
        # Build query
        base_query = select(Keyword)
        count_query = select(func.count(Keyword.id))

        if group_id is not None:
            base_query = base_query.where(Keyword.group_id == group_id)
            count_query = count_query.where(Keyword.group_id == group_id)
        if platform:
            base_query = base_query.where(Keyword.platform == platform)
            count_query = count_query.where(Keyword.platform == platform)
        if status:
            base_query = base_query.where(Keyword.status == status)
            count_query = count_query.where(Keyword.status == status)
        if keyword:
            base_query = base_query.where(Keyword.keyword.contains(keyword))
            count_query = count_query.where(Keyword.keyword.contains(keyword))

        # Get total
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated items
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query.order_by(Keyword.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()

        return KeywordListOut(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                KeywordOut(
                    id=item.id,
                    group_id=item.group_id,
                    keyword=item.keyword,
                    platform=item.platform,
                    source=item.source,
                    status=item.status,
                    crawled_count=item.crawled_count or 0,
                    results_count=item.results_count or 0,
                    notes=item.notes or "",
                    created_at=_format_dt(item.created_at),
                    updated_at=_format_dt(item.updated_at),
                )
                for item in items
            ],
        )


@router.put("/{keyword_id}", response_model=KeywordOut)
async def update_keyword(keyword_id: int, body: KeywordUpdate):
    async with get_mysql_session() as session:
        kw = await session.get(Keyword, keyword_id)
        if not kw:
            raise HTTPException(404, "关键词不存在")

        if body.group_id is not None:
            group = await session.get(KeywordGroup, body.group_id)
            if not group:
                raise HTTPException(404, "分组不存在")
            kw.group_id = body.group_id
        if body.keyword is not None:
            kw.keyword = body.keyword.strip()
        if body.platform is not None:
            kw.platform = body.platform
        if body.source is not None:
            kw.source = body.source
        if body.status is not None:
            kw.status = body.status
        if body.crawled_count is not None:
            kw.crawled_count = body.crawled_count
        if body.results_count is not None:
            kw.results_count = body.results_count
        if body.notes is not None:
            kw.notes = body.notes

        kw.updated_at = datetime.utcnow()
        await session.commit()

        return KeywordOut(
            id=kw.id,
            group_id=kw.group_id,
            keyword=kw.keyword,
            platform=kw.platform,
            source=kw.source,
            status=kw.status,
            crawled_count=kw.crawled_count or 0,
            results_count=kw.results_count or 0,
            notes=kw.notes or "",
            created_at=_format_dt(kw.created_at),
            updated_at=_format_dt(kw.updated_at),
        )


@router.delete("/{keyword_id}")
async def delete_keyword(keyword_id: int):
    async with get_mysql_session() as session:
        kw = await session.get(Keyword, keyword_id)
        if not kw:
            raise HTTPException(404, "关键词不存在")
        await session.delete(kw)
        await session.commit()
        return {"status": "ok", "deleted_keyword_id": keyword_id}


@router.post("/batch-delete")
async def batch_delete_keywords(body: BatchDeleteRequest):
    if not body.ids:
        raise HTTPException(400, "ID 列表不能为空")

    async with get_mysql_session() as session:
        result = await session.execute(
            delete(Keyword).where(Keyword.id.in_(body.ids))
        )
        await session.commit()
        return {"status": "ok", "deleted_count": result.rowcount}


# ── AI Fission Endpoint ────────────────────────────────────────────

def _build_fission_prompt(seed_keyword: str, platform: str, depth: int) -> str:
    if depth == 1:
        count_range = "10-15"
        extra_instruction = "聚焦核心长尾和常见相关词，覆盖主流搜索场景即可。"
    else:
        count_range = "20-30"
        extra_instruction = (
            "需要深度挖掘，覆盖尽可能多的搜索变体、场景和角度。"
            "尽可能列出 20-30 个关键词。"
        )

    platform_name_map = {
        "xhs": "小红书",
        "dy": "抖音",
        "ks": "快手",
        "bili": "B站",
        "wb": "微博",
        "tieba": "贴吧",
        "zhihu": "知乎",
    }
    platform_name = platform_name_map.get(platform, platform)

    return f"""你是一个专业的关键词裂变工具，擅长为内容创作者生成高质量搜索关键词。

目标平台：{platform_name}
种子关键词：「{seed_keyword}」
期望数量：{count_range} 个

请从以下五个维度生成相关关键词：

1. **长尾词**（long_tail）：在种子词基础上添加限定、场景、属性等修饰，形成更具体的长尾关键词
2. **相关词/同义词**（related）：与种子词语义相近、属于同一领域但表达方式不同的词
3. **问句形式**（question）：用户可能以问题形式搜索的关键词，如"怎么""如何""推荐""值得吗"等
4. **地域组合**（regional）：种子词与地域的组合，如城市名、省份名、区域名等
5. **热点/趋势组合**（hot）：与当前热门话题、季节、节日、事件等结合的关键词

{extra_instruction}

请返回严格的 JSON 格式（只返回 JSON，不要 markdown 代码块，不要任何额外文字）：
{{
    "generated": [
        {{"keyword": "关键词文本", "category": "long_tail", "reason": "为什么这个词有价值"}},
        {{"keyword": "关键词文本", "category": "related", "reason": "为什么这个词有价值"}}
    ]
}}

要求：
- 每个关键词必须与种子词「{seed_keyword}」有明确关联
- category 只能是：long_tail, related, question, regional, hot 五种
- reason 用简短中文说明该关键词的搜索价值
- 关键词不要重复
- 关键词要符合{platform_name}平台用户的搜索习惯"""


# ── AI 分类 Prompt 构建 ──────────────────────────────────────────────

def _build_classify_prompt(keyword: str, groups: list[dict]) -> str:
    """构建关键词 AI 分类 prompt"""
    if groups:
        groups_desc = "\n".join([
            f"  - ID={g['id']}, 名称: {g['name']}, 描述: {g.get('description', '')}"
            for g in groups
        ])
        groups_instruction = f"""现有分组列表:
{groups_desc}

请判断上述关键词最应该归属哪个现有分组。如果关键词与某个现有分组高度匹配，返回该分组信息。
如果关键词不属于任何现有分组，请为该关键词建议一个新的分组名称（简洁明了，2-6 个汉字）。"""
    else:
        groups_instruction = "目前还没有任何分组，请为该关键词建议一个新的分组名称（简洁明了，2-6 个汉字）。"

    return f"""你是一个专业的关键词分类助手。请根据关键词的语义和领域，将其归类到最合适的分组中。

关键词: 「{keyword}」

{groups_instruction}

请返回严格的 JSON 格式（只返回 JSON，不要 markdown 代码块，不要任何额外文字）:
{{
    "group_name": "分组名称",
    "is_existing": true,
    "existing_group_id": null,
    "reason": "分类理由（简短中文说明）"
}}

字段说明:
- group_name: 最终的分组名称（已有分组则用原名，新分组则用建议名称）
- is_existing: true 表示归类到已有分组，false 表示需要新建分组
- existing_group_id: 如果 is_existing=true，填写对应分组的数字 ID；否则填 null
- reason: 简短说明为什么这样分类"""


async def _do_classify_keyword(
    kw,  # Keyword ORM 对象
    api_key: str,
    groups: list[dict],
) -> "AutoClassifyResponse":
    """对单个关键词执行 AI 分类，返回分类结果。调用方负责传入 keyword、API Key 和分组列表。"""
    prompt = _build_classify_prompt(kw.keyword, groups)

    # 调用 DeepSeek API
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        ai_text = data["choices"][0]["message"]["content"]

    # 解析 AI 返回的 JSON
    raw_text = ai_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        if len(lines) >= 3:
            lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(500, f"AI 返回内容无法解析为 JSON: {ai_text[:500]}")

    group_name = parsed.get("group_name", "").strip()
    is_existing = parsed.get("is_existing", False)
    existing_group_id = parsed.get("existing_group_id")
    reason = parsed.get("reason", "")

    if not group_name:
        raise HTTPException(500, "AI 未返回有效的分组名称")

    # 查找或创建分组
    group_created = False
    async with get_mysql_session() as session:
        group = None

        # 优先按 ID 查找
        if is_existing and existing_group_id:
            group = await session.get(KeywordGroup, existing_group_id)

        # 按名称查找
        if not group:
            result = await session.execute(
                select(KeywordGroup).where(KeywordGroup.name == group_name)
            )
            group = result.scalar_one_or_none()

        # 找不到则自动创建新分组
        if not group:
            group = KeywordGroup(
                name=group_name,
                description=f"AI 自动创建（关键词: {kw.keyword}）" + (f" — {reason}" if reason else ""),
            )
            session.add(group)
            await session.flush()
            group_created = True

        # 更新关键词的 group_id
        kw_in_session = await session.get(Keyword, kw.id)
        if not kw_in_session:
            raise HTTPException(404, "关键词在分类过程中已被删除")
        kw_in_session.group_id = group.id
        kw_in_session.updated_at = datetime.utcnow()

        await session.commit()

        return AutoClassifyResponse(
            keyword_id=kw.id,
            keyword=kw.keyword,
            group_name=group.name,
            group_id=group.id,
            group_created=group_created,
        )


def _parse_fission_response(ai_text: str, platform: str) -> list[FissionItem]:
    """解析 AI 裂变返回的 JSON，生成带平台信息的 FissionItem 列表"""
    raw_text = ai_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        if len(lines) >= 3:
            lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(500, f"AI 返回内容无法解析为 JSON: {ai_text[:500]}")

    generated_list = parsed.get("generated", [])
    if not isinstance(generated_list, list):
        raise HTTPException(500, "AI 返回格式错误：generated 字段应为数组")

    valid_categories = {"long_tail", "related", "question", "regional", "hot"}
    items: list[FissionItem] = []
    for item in generated_list:
        kw_text = item.get("keyword", "").strip()
        cat = item.get("category", "long_tail").strip()
        reason_text = item.get("reason", "").strip()

        if not kw_text:
            continue
        if cat not in valid_categories:
            cat = "long_tail"

        items.append(FissionItem(keyword=kw_text, platform=platform, category=cat, reason=reason_text))

    return items


@router.post("/fission", response_model=FissionResponse)
async def fission_keywords(req: FissionRequest):
    """AI 关键词裂变 — 支持单平台或多平台（全选）"""
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    # 确定目标平台列表：platforms 优先，兼容旧 platform 字段
    if req.platforms:
        target_platforms = req.platforms
    else:
        target_platforms = [req.platform or "xhs"]

    all_items: list[FissionItem] = []
    seen_keywords: set[str] = set()
    depth = req.depth or 1

    async with httpx.AsyncClient(timeout=90.0) as client:
        for platform in target_platforms:
            prompt = _build_fission_prompt(req.seed_keyword, platform, depth)
            try:
                resp = await client.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                ai_text = data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                raise HTTPException(e.response.status_code, f"DeepSeek API 错误: {e.response.text}")
            except Exception as e:
                raise HTTPException(500, f"请求失败: {str(e)}")

            items = _parse_fission_response(ai_text, platform)

            # 跨平台去重（同关键词只保留第一个平台的）
            for item in items:
                if item.keyword not in seen_keywords:
                    seen_keywords.add(item.keyword)
                    all_items.append(item)

    return FissionResponse(
        seed_keyword=req.seed_keyword,
        platforms=target_platforms,
        generated=all_items,
    )


# ── 关键词 → 爬虫任务关联 ────────────────────────────────────────────

CRAWLER_SERVICE_URL = os.getenv("CRAWLER_SERVICE_URL", "http://127.0.0.1:8081")


class KeywordRunRequest(BaseModel):
    keyword_id: int


class KeywordBatchRunRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)
    mode: Optional[str] = "batch"


class StatusSyncRequest(BaseModel):
    keyword: str
    platform: str
    task_id: Optional[int] = None
    status: Optional[str] = "completed"


@router.post("/run")
async def keyword_run(body: KeywordRunRequest):
    """一键爬取: 单个关键词 → 创建 Crawler-Service 任务"""
    async with get_mysql_session() as session:
        kw = await session.get(Keyword, body.keyword_id)
        if not kw:
            raise HTTPException(404, "关键词不存在")

        # 调用 Crawler-Service 启动爬虫
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{CRAWLER_SERVICE_URL}/api/crawler/start",
                    json={
                        "platform": kw.platform,
                        "keywords": kw.keyword,
                        "crawler_type": "search",
                        "save_option": "db",
                    },
                )
                resp.raise_for_status()
                result = resp.json()
                task_id = result.get("task_id")
        except Exception as e:
            raise HTTPException(500, f"调用 Crawler-Service 失败: {str(e)}")

        # 更新关键词状态
        kw.status = "crawled"
        kw.crawled_count = (kw.crawled_count or 0) + 1
        kw.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "status": "ok",
            "keyword_id": kw.id,
            "keyword": kw.keyword,
            "platform": kw.platform,
            "task_id": task_id,
        }


@router.post("/batch-run")
async def keywords_batch_run(body: KeywordBatchRunRequest):
    """批量爬取: 选中关键词 → 创建任务管道"""
    async with get_mysql_session() as session:
        result = await session.execute(
            select(Keyword).where(Keyword.id.in_(body.ids))
        )
        keywords = result.scalars().all()

        if not keywords:
            raise HTTPException(404, "未找到有效关键词")

        # 按平台分组
        platform_keywords: dict[str, list[str]] = {}
        for kw in keywords:
            platform_keywords.setdefault(kw.platform, []).append(kw.keyword)

        # 为每个平台创建一个管道
        pipelines = []
        for platform, kw_list in platform_keywords.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{CRAWLER_SERVICE_URL}/api/crawler-pro/pipelines",
                        json={
                            "name": f"批量任务_{datetime.now().strftime('%m%d_%H%M')}",
                            "platform": platform,
                            "keywords": kw_list,
                            "mode": body.mode or "batch",
                            "config": {"crawler_type": "search", "save_option": "db"},
                        },
                    )
                    if resp.status_code == 200:
                        pipelines.append(resp.json())
            except Exception:
                pass

        # 更新关键词状态
        for kw in keywords:
            kw.status = "crawled"
            kw.crawled_count = (kw.crawled_count or 0) + 1
            kw.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "status": "ok",
            "total_keywords": len(keywords),
            "platforms": list(platform_keywords.keys()),
            "pipelines": pipelines,
        }


@router.get("/{keyword_id}/tasks")
async def keyword_tasks(keyword_id: int):
    """查询关键词关联的爬虫任务"""
    async with get_mysql_session() as session:
        kw = await session.get(Keyword, keyword_id)
        if not kw:
            raise HTTPException(404, "关键词不存在")

        # 通过 payload_snapshot 查询包含该关键词的任务
        from database.system_models import CrawlerTask
        try:
            # JSON_CONTAINS 查询
            from sqlalchemy import text
            result = await session.execute(
                text(
                    "SELECT id, status, payload_snapshot, created_at, finished_at "
                    "FROM crawler_task "
                    "WHERE JSON_EXTRACT(payload_snapshot, '$.keywords') LIKE :kw "
                    "OR JSON_EXTRACT(payload_snapshot, '$.specific_ids') LIKE :kw2 "
                    "ORDER BY id DESC LIMIT 20"
                ),
                {"kw": f"%{kw.keyword}%", "kw2": f"%{kw.keyword}%"},
            )
            rows = result.fetchall()
            return {
                "keyword_id": kw.id,
                "keyword": kw.keyword,
                "tasks": [
                    {
                        "task_id": row[0], "status": row[1],
                        "created_at": str(row[3]) if row[3] else "",
                        "finished_at": str(row[4]) if row[4] else "",
                    }
                    for row in rows
                ],
            }
        except Exception:
            return {"keyword_id": kw.id, "keyword": kw.keyword, "tasks": []}


@router.post("/status-sync")
async def sync_keyword_status(body: StatusSyncRequest):
    """同步关键词状态 (由 PipelineExecutor 调用)"""
    async with get_mysql_session() as session:
        result = await session.execute(
            select(Keyword).where(
                Keyword.keyword == body.keyword,
                Keyword.platform == body.platform,
            )
        )
        kw = result.scalar_one_or_none()
        if kw:
            if body.status == "completed":
                kw.status = "has_results"
            elif body.status == "failed":
                kw.status = "no_results"
            kw.crawled_count = (kw.crawled_count or 0) + 1
            kw.updated_at = datetime.utcnow()
            await session.commit()
            return {"status": "ok", "keyword_id": kw.id}
        return {"status": "ok", "message": "关键词未找到，跳过同步"}


# ── Keyword Statistics ──────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_keyword_stats():
    async with get_mysql_session() as session:
        # Total count
        total_result = await session.execute(
            select(func.count(Keyword.id))
        )
        total_keywords = total_result.scalar() or 0

        # By group
        group_result = await session.execute(
            select(
                KeywordGroup.name,
                func.count(Keyword.id),
            )
            .outerjoin(Keyword, Keyword.group_id == KeywordGroup.id)
            .group_by(KeywordGroup.id)
            .order_by(func.count(Keyword.id).desc())
        )
        by_group = [
            StatsByGroup(group_name=row[0], count=row[1] or 0)
            for row in group_result.all()
        ]

        # By status
        status_result = await session.execute(
            select(
                Keyword.status,
                func.count(Keyword.id),
            )
            .group_by(Keyword.status)
            .order_by(func.count(Keyword.id).desc())
        )
        by_status = [
            StatsByStatus(status=row[0], count=row[1] or 0)
            for row in status_result.all()
        ]

        # Top performing (by results_count)
        top_result = await session.execute(
            select(
                Keyword.keyword,
                Keyword.results_count,
                Keyword.crawled_count,
            )
            .order_by(Keyword.results_count.desc())
            .limit(10)
        )
        top_performing = [
            TopPerforming(
                keyword=row[0],
                results_count=row[1] or 0,
                crawled_count=row[2] or 0,
            )
            for row in top_result.all()
        ]

        return StatsResponse(
            total_keywords=total_keywords,
            by_group=by_group,
            by_status=by_status,
            top_performing=top_performing,
        )
