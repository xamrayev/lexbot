"""Agent catalog + plan info for the current tenant."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models import User
from app.schemas import AgentOut, PlanOut
from app.services.agents.definitions import AGENTS
from app.services.billing.plans import get_tenant_plan

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentOut])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await get_tenant_plan(db, user.tenant_id)
    return [
        AgentOut(
            slug=a.slug,
            name=a.name,
            description=a.description,
            min_tier=a.min_tier,
            available=a.slug in plan.agents,
        )
        for a in AGENTS.values()
    ]


@router.get("/billing/plan", response_model=PlanOut)
async def current_plan(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await get_tenant_plan(db, user.tenant_id)
    return PlanOut(
        tier=plan.tier,
        messages_per_day=plan.messages_per_day,
        documents_per_day=plan.documents_per_day,
        max_users=plan.max_users,
        document_upload=plan.document_upload,
        corporate_knowledge_base=plan.corporate_knowledge_base,
        multi_agent=plan.multi_agent,
        agents=plan.agents,
    )
