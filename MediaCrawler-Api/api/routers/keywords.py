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
    depth: Optional[int] = Field(1, ge=1, le=2)


class FissionItem(BaseModel):
    keyword: str
    category: str
    reason: str


class FissionResponse(BaseModel):
    seed_keyword: str
    platform: str
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
async def create_keyword(body: KeywordCreate):
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


@router.post("/fission", response_model=FissionResponse)
async def fission_keywords(req: FissionRequest):
    # ── 阶段 1: 检查 API Key ─────────────────────────────────────
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY，请在 .env 中设置")

    # ── 阶段 2: 调用 DeepSeek API（不持有 DB 连接）──────────────
    prompt = _build_fission_prompt(req.seed_keyword, req.platform or "xhs", req.depth or 1)

    async with httpx.AsyncClient(timeout=90.0) as client:
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

    # ── 阶段 3: 解析 JSON ───────────────────────────────────────
    raw_text = ai_text.strip()
    # Strip markdown code block if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        if len(lines) >= 3:
            lines = lines[1:]  # Remove ```json or ```
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

        items.append(FissionItem(keyword=kw_text, category=cat, reason=reason_text))

    return FissionResponse(
        seed_keyword=req.seed_keyword,
        platform=req.platform or "xhs",
        generated=items,
    )


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
