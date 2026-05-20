# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from sqlalchemy import select, delete

from database.db_session import get_mysql_session
from database.system_models import ChatSession, ChatMemory

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
