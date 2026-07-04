"""Chat endpoint: plan-limit check → agent run → persisted conversation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.db.base import get_db
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, ConversationOut
from app.services.agents.definitions import AGENTS
from app.services.agents.runner import run_agent_turn
from app.services.ai.base import ChatMessage
from app.services.billing.plans import PlanLimitExceeded, check_and_increment, get_tenant_plan

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

    # Load or create the conversation (tenant- and user-scoped)
    conversation: Conversation | None = None
    history: list[ChatMessage] = []
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
    if conversation is None:
        conversation = Conversation(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.id,
            agent=body.agent,
            title=body.message[:80],
        )
        db.add(conversation)
        await db.flush()

    reply = await run_agent_turn(
        db,
        tenant_id=user.tenant_id,
        agent_slug=body.agent,
        user_message=body.message,
        history=history,
        provider_name=body.provider,
    )

    db.add(Message(conversation_id=conversation.id, role="user", content=body.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=reply.content, sources=reply.sources))
    await write_audit(db, request, user, "chat.message", resource=str(conversation.id), detail={"agent": body.agent})
    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        content=reply.content,
        sources=reply.sources,
        blocked=reply.blocked,
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
