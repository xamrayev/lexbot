"""Agent execution: guardrails → RAG retrieval → LLM completion with citations."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.definitions import get_agent
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_provider
from app.services.rag.pipeline import retrieve
from app.services.security.guard import screen_user_input, wrap_retrieved_context

MAX_HISTORY_MESSAGES = 20


@dataclass
class AgentReply:
    content: str
    sources: list[dict] = field(default_factory=list)
    blocked: bool = False


async def run_agent_turn(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_slug: str,
    user_message: str,
    history: list[ChatMessage] | None = None,
    provider_name: str | None = None,
) -> AgentReply:
    verdict = screen_user_input(user_message)
    if not verdict.allowed:
        return AgentReply(
            content="Запрос отклонён системой безопасности. Переформулируйте вопрос.",
            blocked=True,
        )

    agent = get_agent(agent_slug)
    rag = await retrieve(db, tenant_id, user_message)

    messages: list[ChatMessage] = [ChatMessage(role="system", content=agent.system_prompt)]
    if rag.context:
        messages.append(ChatMessage(role="system", content=wrap_retrieved_context(rag.context)))
    messages.extend((history or [])[-MAX_HISTORY_MESSAGES:])
    messages.append(ChatMessage(role="user", content=user_message))

    result = await get_provider(provider_name).complete(messages)
    return AgentReply(content=result.content, sources=rag.sources)
