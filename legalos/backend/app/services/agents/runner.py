"""Agent execution: guardrails → RAG retrieval → LLM completion with citations."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.definitions import get_agent
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_provider
from app.services.rag.pipeline import retrieve
from app.services.security.guard import screen_user_input_deep, wrap_retrieved_context

MAX_HISTORY_MESSAGES = 20

BLOCKED_MESSAGE = "Запрос отклонён системой безопасности. Переформулируйте вопрос."


@dataclass
class PreparedTurn:
    messages: list[ChatMessage]
    sources: list[dict] = field(default_factory=list)
    blocked: bool = False


@dataclass
class AgentReply:
    content: str
    sources: list[dict] = field(default_factory=list)
    blocked: bool = False


async def prepare_turn(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_slug: str,
    user_message: str,
    history: list[ChatMessage] | None = None,
) -> PreparedTurn:
    """Shared first half of a turn: guardrails, retrieval, prompt assembly."""
    verdict = await screen_user_input_deep(user_message)
    if not verdict.allowed:
        return PreparedTurn(messages=[], blocked=True)

    agent = get_agent(agent_slug)
    rag = await retrieve(db, tenant_id, user_message)

    messages: list[ChatMessage] = [ChatMessage(role="system", content=agent.system_prompt)]
    if rag.context:
        messages.append(ChatMessage(role="system", content=wrap_retrieved_context(rag.context)))
    messages.extend((history or [])[-MAX_HISTORY_MESSAGES:])
    messages.append(ChatMessage(role="user", content=user_message))
    return PreparedTurn(messages=messages, sources=rag.sources)


async def run_agent_turn(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_slug: str,
    user_message: str,
    history: list[ChatMessage] | None = None,
    provider_name: str | None = None,
) -> AgentReply:
    turn = await prepare_turn(
        db, tenant_id=tenant_id, agent_slug=agent_slug, user_message=user_message, history=history
    )
    if turn.blocked:
        return AgentReply(content=BLOCKED_MESSAGE, blocked=True)
    result = await get_provider(provider_name).complete(turn.messages)
    return AgentReply(content=result.content, sources=turn.sources)


async def stream_agent_turn(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_slug: str,
    user_message: str,
    history: list[ChatMessage] | None = None,
    provider_name: str | None = None,
) -> tuple[PreparedTurn, AsyncIterator[str] | None]:
    """Prepare a turn and return a token iterator (None when blocked)."""
    turn = await prepare_turn(
        db, tenant_id=tenant_id, agent_slug=agent_slug, user_message=user_message, history=history
    )
    if turn.blocked:
        return turn, None
    return turn, get_provider(provider_name).stream(turn.messages)
