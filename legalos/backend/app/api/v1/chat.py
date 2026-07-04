"""Chat endpoints: plan-limit check → agent run → persisted conversation.

POST /chat        — request/response JSON
POST /chat/stream — Server-Sent Events: {"delta": "..."} tokens, then
                    {"done": true, "conversation_id": ..., "sources": [...]}
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.db.base import get_db
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, ConversationOut
from app.services.agents.definitions import AGENTS
from app.services.agents.runner import BLOCKED_MESSAGE, run_agent_turn, stream_agent_turn
from app.services.ai.base import ChatMessage
from app.services.billing.plans import PlanLimitExceeded, check_and_increment, get_tenant_plan

router = APIRouter(prefix="/chat", tags=["chat"])


async def _authorize_turn(db: AsyncSession, user: User, body: ChatRequest) -> None:
    if body.agent not in AGENTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown agent '{body.agent}'")
    plan = await get_tenant_plan(db, user.tenant_id)
    if body.agent not in plan.agents:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Agent '{body.agent}' requires a higher plan (current: {plan.tier.value})",
        )
    try:
        await check_and_increment(db, user, "messages")
    except PlanLimitExceeded as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e))


async def _load_or_create_conversation(
    db: AsyncSession, user: User, body: ChatRequest
) -> tuple[Conversation, list[ChatMessage]]:
    if body.conversation_id is not None:
        row = await db.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.tenant_id == user.tenant_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = row.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        rows = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
        )
        history = [ChatMessage(role=m.role, content=m.content) for m in rows.scalars()]
        return conversation, history

    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.id,
        agent=body.agent,
        title=body.message[:80],
    )
    db.add(conversation)
    await db.flush()
    return conversation, []


async def _persist_turn(
    db: AsyncSession,
    request: Request,
    user: User,
    conversation: Conversation,
    body: ChatRequest,
    answer: str,
    sources: list[dict],
) -> None:
    db.add(Message(conversation_id=conversation.id, role="user", content=body.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer, sources=sources))
    await write_audit(db, request, user, "chat.message", resource=str(conversation.id), detail={"agent": body.agent})
    await db.commit()


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_turn(db, user, body)
    conversation, history = await _load_or_create_conversation(db, user, body)

    reply = await run_agent_turn(
        db,
        tenant_id=user.tenant_id,
        agent_slug=body.agent,
        user_message=body.message,
        history=history,
        provider_name=body.provider,
    )
    await _persist_turn(db, request, user, conversation, body, reply.content, reply.sources)
    return ChatResponse(
        conversation_id=conversation.id,
        content=reply.content,
        sources=reply.sources,
        blocked=reply.blocked,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_turn(db, user, body)
    conversation, history = await _load_or_create_conversation(db, user, body)

    turn, token_stream = await stream_agent_turn(
        db,
        tenant_id=user.tenant_id,
        agent_slug=body.agent,
        user_message=body.message,
        history=history,
        provider_name=body.provider,
    )

    async def event_source():
        if token_stream is None:  # blocked by the security screen
            await _persist_turn(db, request, user, conversation, body, BLOCKED_MESSAGE, [])
            yield _sse({"delta": BLOCKED_MESSAGE, "blocked": True})
            yield _sse({"done": True, "conversation_id": str(conversation.id), "sources": [], "blocked": True})
            return
        parts: list[str] = []
        try:
            async for token in token_stream:
                parts.append(token)
                yield _sse({"delta": token})
        except Exception:
            yield _sse({"error": "generation failed"})
        answer = "".join(parts)
        if answer:
            await _persist_turn(db, request, user, conversation, body, answer, turn.sources)
        yield _sse({"done": True, "conversation_id": str(conversation.id), "sources": turn.sources})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Conversation)
        .where(Conversation.tenant_id == user.tenant_id, Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(100)
    )
    return list(rows.scalars())
