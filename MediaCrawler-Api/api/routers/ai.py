# -*- coding: utf-8 -*-
import os
import json
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from sqlalchemy import select, delete

from database.db_session import get_mysql_session
from database.system_models import ChatSession, ChatMemory
from services.data_query_service import DataQueryService, PLATFORM_META

router = APIRouter(prefix="/ai", tags=["ai"])

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


# ── Pydantic Models ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: int | None = None
    messages: list[ChatMessage]
    model: str = "deepseek-chat"


class ChatResponse(BaseModel):
    content: str
    model: str
    session_id: int


class SessionCreate(BaseModel):
    title: str = "新对话"


class SessionRename(BaseModel):
    title: str


class SessionOut(BaseModel):
    id: int
    title: str
    message_count: int
    created_at: str
    updated_at: str


class MemoryCreate(BaseModel):
    key: str
    content: str
    category: str = "通用"


class MemoryOut(BaseModel):
    id: int
    key: str
    content: str
    category: str
    created_at: str
    updated_at: str


# ── Helpers ──────────────────────────────────────────────────────

def _get_api_key() -> str:
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    return os.getenv("DEEPSEEK_API_KEY", "")


def _format_dt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _tokenize_for_match(text: str) -> list[str]:
    """将文本拆分为可用于模糊匹配的 token 列表，同时支持中英文。"""
    tokens = []
    # 按标点/空白拆分，同时保留连续的中文字符段作为 token
    parts = re.split(r'[，。！？、；：""''（）\s,\.!\?;:\"'']+', text.lower())
    for part in parts:
        part = part.strip()
        if not part:
            continue
        tokens.append(part)
        # 对纯中文段，额外拆分为 2-gram 子串以提高匹配召回率
        if re.match(r'^[一-鿿]+$', part) and len(part) >= 3:
            for i in range(len(part) - 1):
                tokens.append(part[i:i + 2])
    return [t for t in tokens if len(t) >= 2]


async def _get_related_memories(user_message: str) -> str:
    """检索与用户消息相关的记忆，组装成 system prompt 片段。"""
    async with get_mysql_session() as session:
        result = await session.execute(select(ChatMemory))
        memories = result.scalars().all()

    if not memories:
        return ""

    msg_tokens = set(_tokenize_for_match(user_message))
    if not msg_tokens:
        return ""

    relevant: list[str] = []
    for m in memories:
        score = 0
        key_tokens = set(_tokenize_for_match(m.key))
        score += len(msg_tokens & key_tokens) * 2  # key 匹配权重更高

        content_tokens = set(_tokenize_for_match(m.content))
        score += len(msg_tokens & content_tokens)

        if score >= 1:
            relevant.append((score, f"- {m.key}: {m.content}"))

    relevant.sort(key=lambda x: x[0], reverse=True)

    if not relevant:
        return ""

    lines = [line for _, line in relevant[:5]]
    return "以下是用户之前告诉你的重要信息，请在回答时参考：\n" + "\n".join(lines)


# ── Chat ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY")

    # ── 阶段 1: 数据库操作（短期持有连接）─────────────────────────
    session_id = req.session_id
    async with get_mysql_session() as db:
        if session_id:
            db_session = await db.get(ChatSession, session_id)
            if not db_session:
                raise HTTPException(404, "会话不存在")
        else:
            first_msg = req.messages[0].content if req.messages else "新对话"
            title = first_msg[:20] + ("..." if len(first_msg) > 20 else "")
            db_session = ChatSession(title=title, messages=[])
            db.add(db_session)
            await db.flush()
            session_id = db_session.id
        await db.commit()
    # ── DB 会话已关闭 ─────────────────────────────────────────────

    # ── 阶段 2: 检索记忆（独立的短期 DB 会话）─────────────────────
    user_msg = req.messages[-1].content if req.messages else ""
    memory_prompt = await _get_related_memories(user_msg)

    # ── 阶段 3: 调用 DeepSeek API（不持有任何 DB 连接）────────────
    api_messages: list[dict] = []
    if memory_prompt:
        api_messages.append({"role": "system", "content": memory_prompt})
    for m in req.messages:
        api_messages.append({"role": m.role, "content": m.content})

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": req.model, "messages": api_messages},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"DeepSeek API 错误: {e.response.text}")
        except Exception as e:
            raise HTTPException(500, f"请求失败: {str(e)}")

    # ── 阶段 4: 保存消息到 DB（短期连接）───────────────────────
    now = datetime.utcnow().isoformat()

    async with get_mysql_session() as db:
        db_session = await db.get(ChatSession, session_id)
        if db_session:
            existing = list(db_session.messages) if db_session.messages else []
            existing.append({"role": "user", "content": user_msg, "timestamp": now})
            existing.append({"role": "assistant", "content": content, "timestamp": now})
            db_session.messages = existing
            db_session.updated_at = datetime.utcnow()
            await db.commit()

    return ChatResponse(content=content, model=req.model, session_id=session_id)


# ── Sessions ─────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions():
    async with get_mysql_session() as session:
        result = await session.execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc())
        )
        rows = result.scalars().all()
        return [
            SessionOut(
                id=r.id,
                title=r.title,
                message_count=len(r.messages) if r.messages else 0,
                created_at=_format_dt(r.created_at),
                updated_at=_format_dt(r.updated_at),
            )
            for r in rows
        ]


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: int):
    async with get_mysql_session() as session:
        r = await session.get(ChatSession, session_id)
        if not r:
            raise HTTPException(404, "会话不存在")
        return SessionOut(
            id=r.id,
            title=r.title,
            message_count=len(r.messages) if r.messages else 0,
            created_at=_format_dt(r.created_at),
            updated_at=_format_dt(r.updated_at),
        )


@router.post("/sessions", response_model=SessionOut)
async def create_session(req: SessionCreate):
    async with get_mysql_session() as session:
        s = ChatSession(title=req.title, messages=[])
        session.add(s)
        await session.flush()
        await session.commit()
        return SessionOut(
            id=s.id,
            title=s.title,
            message_count=0,
            created_at=_format_dt(s.created_at),
            updated_at=_format_dt(s.updated_at),
        )


@router.put("/sessions/{session_id}")
async def rename_session(session_id: int, req: SessionRename):
    async with get_mysql_session() as session:
        s = await session.get(ChatSession, session_id)
        if not s:
            raise HTTPException(404, "会话不存在")
        s.title = req.title
        s.updated_at = datetime.utcnow()
        await session.commit()
        return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    async with get_mysql_session() as session:
        await session.execute(delete(ChatSession).where(ChatSession.id == session_id))
        await session.commit()
        return {"ok": True}


# ── Memories ─────────────────────────────────────────────────────

@router.get("/memories", response_model=list[MemoryOut])
async def list_memories():
    async with get_mysql_session() as session:
        result = await session.execute(
            select(ChatMemory).order_by(ChatMemory.updated_at.desc())
        )
        rows = result.scalars().all()
        return [
            MemoryOut(
                id=r.id,
                key=r.key,
                content=r.content,
                category=r.category,
                created_at=_format_dt(r.created_at),
                updated_at=_format_dt(r.updated_at),
            )
            for r in rows
        ]


@router.post("/memories", response_model=MemoryOut)
async def create_memory(req: MemoryCreate):
    async with get_mysql_session() as session:
        result = await session.execute(select(ChatMemory).where(ChatMemory.key == req.key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.content = req.content
            existing.category = req.category
            existing.updated_at = datetime.utcnow()
            await session.commit()
            return MemoryOut(
                id=existing.id, key=existing.key, content=existing.content,
                category=existing.category,
                created_at=_format_dt(existing.created_at),
                updated_at=_format_dt(existing.updated_at),
            )

        m = ChatMemory(key=req.key, content=req.content, category=req.category)
        session.add(m)
        await session.flush()
        await session.commit()
        return MemoryOut(
            id=m.id, key=m.key, content=m.content, category=m.category,
            created_at=_format_dt(m.created_at),
            updated_at=_format_dt(m.updated_at),
        )


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: int):
    async with get_mysql_session() as session:
        await session.execute(delete(ChatMemory).where(ChatMemory.id == memory_id))
        await session.commit()
        return {"ok": True}


# ── Messages ─────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int):
    async with get_mysql_session() as session:
        s = await session.get(ChatSession, session_id)
        if not s:
            raise HTTPException(404, "会话不存在")
        return {"session_id": session_id, "messages": s.messages or []}


# ── Analyze Comments Pydantic Models ──────────────────────────────

class SentimentAnalysis(BaseModel):
    positive: float
    neutral: float
    negative: float
    summary: str


class KeyInsight(BaseModel):
    point: str
    representative_comment: str


class AnalyzeRequest(BaseModel):
    platform: str
    content_id: str


class AnalyzeResponse(BaseModel):
    platform: str
    content_id: str
    comment_count: int
    sentiment: SentimentAnalysis
    key_insights: list[KeyInsight]
    summary: str
    hot_topics: list[str]


# ── Analyze Comments ──────────────────────────────────────────────

_MAX_COMMENTS = 500
_PAGE_SIZE = 100


@router.post("/analyze-comments", response_model=AnalyzeResponse)
async def analyze_comments(req: AnalyzeRequest):
    # ── 阶段 1: 校验平台 ─────────────────────────────────────────
    if req.platform not in PLATFORM_META:
        raise HTTPException(400, f"不支持的平台: {req.platform}")

    # ── 阶段 2: 分页拉取评论（每页 100 条，最多 5 页）──────────
    all_comments: list[str] = []
    total_count = 0
    truncated = False

    for page in range(1, 6):  # 最多 5 页，每页 100 条 = 最多 500 条
        result = await DataQueryService.query_comments_by_content(
            platform=req.platform,
            content_id=req.content_id,
            page=page,
            page_size=_PAGE_SIZE,
        )
        items = result.get("items", [])
        total_count = result.get("total", 0)

        for item in items:
            comment_text = item.get("content", "") if item.get("content") else ""
            if comment_text and isinstance(comment_text, str):
                comment_text = comment_text.strip()
                if comment_text:
                    all_comments.append(comment_text)

        if len(items) < _PAGE_SIZE:
            break

    # 检查实际拉取数量是否超过 500
    if len(all_comments) >= _MAX_COMMENTS:
        all_comments = all_comments[:_MAX_COMMENTS]
        truncated = True

    # ── 阶段 3: 无评论时返回空分析 ──────────────────────────────
    comment_count = len(all_comments)
    if comment_count == 0:
        return AnalyzeResponse(
            platform=req.platform,
            content_id=req.content_id,
            comment_count=0,
            sentiment=SentimentAnalysis(
                positive=0,
                neutral=0,
                negative=0,
                summary="该内容暂无评论数据",
            ),
            key_insights=[],
            summary="该内容下没有评论，无法进行分析",
            hot_topics=[],
        )

    # ── 阶段 4: 构建 Prompt ──────────────────────────────────────
    truncated_notice = ""
    if truncated:
        truncated_notice = f"（注意：原始评论超过{_MAX_COMMENTS}条，此处仅展示了前{_MAX_COMMENTS}条）\n"

    comments_text = "\n".join(
        f"{i+1}. {c}" for i, c in enumerate(all_comments)
    )

    prompt = f"""请分析以下{comment_count}条用户评论，返回严格的JSON格式分析结果。

{truncated_notice}评论列表：
{comments_text}

要求返回以下JSON结构（只返回JSON，不要markdown代码块，不要任何额外文字）：
{{
    "sentiment": {{
        "positive": 正面评论百分比(整数),
        "neutral": 中性评论百分比(整数),
        "negative": 负面评论百分比(整数),
        "summary": "情感分析小结，用中文"
    }},
    "key_insights": [
        {{"point": "核心观点概述", "representative_comment": "代表性评论原文"}}
    ],
    "summary": "综合总结，包括评论数量、整体情感倾向、主要讨论话题等",
    "hot_topics": ["热门话题1", "热门话题2", ...]
}}

注意：positive + neutral + negative 三者之和必须等于 100。"""

    # ── 阶段 5: 调用 DeepSeek API ────────────────────────────────
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(500, "未配置 DEEPSEEK_API_KEY")

    async with httpx.AsyncClient(timeout=180.0) as client:
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

    # ── 阶段 6: 解析 JSON ────────────────────────────────────────
    parsed: dict = {}
    raw_text = ai_text.strip()
    # 尝试去掉可能的 markdown 代码块包裹
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # 去掉第一行和最后一行 ``` 标记
        if len(lines) >= 3:
            lines = lines[1:]  # 去掉 ```json 或 ```
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(500, f"AI 返回内容无法解析为 JSON: {ai_text[:500]}")
    except Exception as e:
        raise HTTPException(500, f"解析 AI 返回结果时出错: {str(e)}")

    # ── 阶段 7: 构造响应 ─────────────────────────────────────────
    sentiment_data = parsed.get("sentiment", {})
    key_insights_data = parsed.get("key_insights", [])
    summary_text = parsed.get("summary", "")
    hot_topics_data = parsed.get("hot_topics", [])

    # 如果评论被截断，在总结中注明
    if truncated:
        summary_text = f"（注意：原始评论超过{_MAX_COMMENTS}条，仅分析了前{_MAX_COMMENTS}条）{summary_text}"

    return AnalyzeResponse(
        platform=req.platform,
        content_id=req.content_id,
        comment_count=comment_count,
        sentiment=SentimentAnalysis(
            positive=round(sentiment_data.get("positive", 0)),
            neutral=round(sentiment_data.get("neutral", 0)),
            negative=round(sentiment_data.get("negative", 0)),
            summary=sentiment_data.get("summary", ""),
        ),
        key_insights=[
            KeyInsight(
                point=k.get("point", ""),
                representative_comment=k.get("representative_comment", ""),
            )
            for k in key_insights_data
        ],
        summary=summary_text,
        hot_topics=hot_topics_data,
    )
