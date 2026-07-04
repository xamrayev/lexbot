"""Subscription tiers and limit enforcement.

Tiers follow the product ladder: Free → HR Pro → Business → Enterprise →
Government Edition. Limits are enforced per user per day via UsageCounter.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlanTier, Subscription, UsageCounter, User

UNLIMITED = -1


@dataclass(frozen=True)
class PlanLimits:
    tier: PlanTier
    messages_per_day: int
    documents_per_day: int
    max_users: int
    document_upload: bool
    corporate_knowledge_base: bool
    multi_agent: bool
    agents: list[str] = field(default_factory=list)


PLANS: dict[PlanTier, PlanLimits] = {
    PlanTier.free: PlanLimits(
        tier=PlanTier.free,
        messages_per_day=20,
        documents_per_day=2,
        max_users=1,
        document_upload=False,
        corporate_knowledge_base=False,
        multi_agent=False,
        agents=["hr"],  # labor law only
    ),
    PlanTier.hr_pro: PlanLimits(
        tier=PlanTier.hr_pro,
        messages_per_day=200,
        documents_per_day=50,
        max_users=1,
        document_upload=True,
        corporate_knowledge_base=False,
        multi_agent=False,
        agents=["hr"],
    ),
    PlanTier.business: PlanLimits(
        tier=PlanTier.business,
        messages_per_day=1000,
        documents_per_day=500,
        max_users=50,
        document_upload=True,
        corporate_knowledge_base=True,
        multi_agent=True,
        agents=["hr", "legal", "accounting", "procurement", "ceo", "tax"],
    ),
    PlanTier.enterprise: PlanLimits(
        tier=PlanTier.enterprise,
        messages_per_day=UNLIMITED,
        documents_per_day=UNLIMITED,
        max_users=UNLIMITED,
        document_upload=True,
        corporate_knowledge_base=True,
        multi_agent=True,
        agents=["hr", "legal", "accounting", "procurement", "ceo", "compliance", "tax"],
    ),
    PlanTier.government: PlanLimits(
        tier=PlanTier.government,
        messages_per_day=UNLIMITED,
        documents_per_day=UNLIMITED,
        max_users=UNLIMITED,
        document_upload=True,
        corporate_knowledge_base=True,
        multi_agent=True,
        agents=["hr", "legal", "accounting", "procurement", "ceo", "compliance", "tax"],
    ),
}


async def get_tenant_plan(db: AsyncSession, tenant_id) -> PlanLimits:
    row = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    subscription = row.scalar_one_or_none()
    if subscription is None:
        return PLANS[PlanTier.free]
    if subscription.valid_until is not None and subscription.valid_until < datetime.now(timezone.utc):
        return PLANS[PlanTier.free]  # expired subscription degrades to Free
    return PLANS[subscription.tier]


class PlanLimitExceeded(Exception):
    def __init__(self, metric: str, limit: int) -> None:
        self.metric = metric
        self.limit = limit
        super().__init__(f"Daily limit exceeded for '{metric}' ({limit}/day)")


async def check_and_increment(db: AsyncSession, user: User, metric: str) -> None:
    """Raise PlanLimitExceeded if the user's daily quota for `metric` is spent,
    otherwise increment the counter."""
    plan = await get_tenant_plan(db, user.tenant_id)
    limit = {"messages": plan.messages_per_day, "documents": plan.documents_per_day}.get(metric, UNLIMITED)

    today = date.today().isoformat()
    row = await db.execute(
        select(UsageCounter).where(
            UsageCounter.tenant_id == user.tenant_id,
            UsageCounter.user_id == user.id,
            UsageCounter.day == today,
            UsageCounter.metric == metric,
        )
    )
    counter = row.scalar_one_or_none()
    if counter is None:
        counter = UsageCounter(tenant_id=user.tenant_id, user_id=user.id, day=today, metric=metric, value=0)
        db.add(counter)
    if limit != UNLIMITED and counter.value >= limit:
        raise PlanLimitExceeded(metric, limit)
    counter.value += 1
    await db.flush()
