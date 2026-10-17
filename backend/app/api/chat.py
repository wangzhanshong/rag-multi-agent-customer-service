"""对话 API —— SSE 流式输出，通过调度Agent分发到专家Agent。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from openai.types.responses import ResponseTextDeltaEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agents.triage import triage_agent
from app.db.models import Conversation, Message
from app.db.mysql import async_session_factory, get_db
from app.models.chat import (
    ChatRequest,
    ConversationDetail,
    ConversationMeta,
    IntentType,
    MessageItem,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/bm25-debug")
async def bm25_debug(q: str = "电脑无法开机"):
    """调试端点：查看 BM25 索引状态。"""
    from app.rag.retrieval import _bm25_index, retrieve
    results = await retrieve(q, top_k=5)
    return {
        "bm25_doc_count": _bm25_index._N,
        "query": q,
        "results": [{"title": r.title, "score": round(r.score, 3), "text": r.chunk_text[:100]} for r in results],
    }


@router.post("")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """对话接口 —— SSE 流式输出。

    流程: 用户消息 → Triage Agent (意图识别) → handoff → 专家Agent → 流式回复。
    """

    session_id = request.session_id

    conv = (await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )).scalar_one_or_none()
    if conv is None:
        conv = Conversation(session_id=session_id, title=request.message[:30])
        db.add(conv)
        await db.commit()

    user_msg = Message(conversation_id=conv.id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    conv_id = conv.id

    async def event_generator():
        from agents import Runner

        assistant_text_parts: list[str] = []
        last_agent_name: str = "Triage Agent"
        sources: list[dict] = []

        try:
            yield {"event": "thinking", "data": None}

            result = Runner.run_streamed(
                starting_agent=triage_agent,
                input=request.message,
            )

            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    evt_data = event.data
                    if isinstance(evt_data, ResponseTextDeltaEvent):
                        assistant_text_parts.append(evt_data.delta)
                        yield {"event": "token", "data": evt_data.delta}

                elif event.type == "run_item_stream_event":
                    if event.name == "handoff_occured":
                        last_agent_name = getattr(event.item, "agent_name", "unknown")
                    elif event.name == "tool_called":
                        tool_name = getattr(event.item, "tool_name", "")
                        if tool_name == "rag_search":
                            yield {"event": "thinking", "data": "正在检索知识库..."}

        except Exception as exc:
            yield {"event": "error", "data": str(exc)}
            return

        # 从 Agent 运行结果中提取 RAG 来源
        # 方式1: 从 to_input_list 中提取 function_call_output
        try:
            for item in result.to_input_list():
                if item.get("type") == "function_call_output":
                    output = str(item.get("output", ""))
                    for line in output.split("\n"):
                        if line.startswith("[") and "标题:" in line:
                            title = line.split("标题:", 1)[1].strip()
                            if title and title not in [s.get("title") for s in sources]:
                                sources.append({"title": title})
        except Exception:
            pass

        # 方式2: 从回复文本中提取 【来源: xxx】 标记
        full_text = "".join(assistant_text_parts)
        import re
        for m in re.finditer(r"【来源[:：]\s*(.+?)】", full_text):
            title = m.group(1).strip()
            if title and title not in [s.get("title") for s in sources]:
                sources.append({"title": title})

        intent_map = {
            "Tech Expert": IntentType.TECH,
            "Nav Expert": IntentType.NAV,
            "General Agent": IntentType.GENERAL,
        }
        intent = intent_map.get(last_agent_name, IntentType.GENERAL)

        async with async_session_factory() as session:
            assistant_msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=full_text,
                intent=intent.value,
                sources=json.dumps(sources, ensure_ascii=False),
            )
            session.add(assistant_msg)
            await session.commit()

        yield {"event": "source", "data": json.dumps(sources, ensure_ascii=False)}
        yield {"event": "done", "data": None}

    return EventSourceResponse(event_generator())


@router.get("/conversations", response_model=list[ConversationMeta])
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[ConversationMeta]:
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(50)
    )
    records = result.scalars().all()
    return [
        ConversationMeta(
            session_id=r.session_id,
            title=r.title,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.get("/conversations/{session_id}", response_model=ConversationDetail | None)
async def get_conversation(session_id: str, db: AsyncSession = Depends(get_db)) -> ConversationDetail | None:
    conv = (await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )).scalar_one_or_none()
    if conv is None:
        return None

    messages_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    return ConversationDetail(
        session_id=conv.session_id,
        title=conv.title,
        messages=[
            MessageItem(
                role=m.role,
                content=m.content,
                intent=IntentType(m.intent) if m.intent else None,
                sources=json.loads(m.sources) if m.sources else [],
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )
