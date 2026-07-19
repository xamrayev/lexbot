"""Redis-backed usage counters and IP rate limiting.

Daily plan quotas live in Redis (atomic INCR + EXPIRE to end of day) instead
of row-per-increment PostgreSQL transactions; the PG ``usage_counters`` table
is kept as statistics via periodic writeback (every Nth increment). When Redis
is unreachable the limiter transparently falls back to the original
PostgreSQL implementation — quota enforcement never goes down with Redis.

Also provides a fixed-window per-IP rate limit used on ``/auth/*`` endpoints
to slow down brute force (fails open on Redis errors).
"""

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis
from app.models import User

log = logging.getLogger("legalos.limiter")


def _seconds_until_midnight(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return max(60, int((tomorrow - now).total_seconds()))


async def check_and_increment_redis(db: AsyncSession, user: User, metric: str) -> None:
    """Redis-first quota check; falls back to the PG implementation.

    Raises PlanLimitExceeded when the user's daily quota for `metric` is spent.
    """
    from app.services.billing.plans import (
        UNLIMITED,
        PlanLimitExceeded,
        check_and_increment as pg_check_and_increment,
        get_tenant_plan,
    )

    plan = await get_tenant_plan(db, user.tenant_id)
    limit = {"messages": plan.messages_per_day, "documents": plan.documents_per_day}.get(metric, UNLIMITED)
    if limit == UNLIMITED:
        return

    day = date.today().isoformat()
    key = f"usage:{user.tenant_id}:{user.id}:{day}:{metric}"
    try:
        redis = get_redis()
        value = await redis.incr(key)
        if value == 1:
            await redis.expire(key, _seconds_until_midnight())
        if value > limit:
            await redis.decr(key)  # the rejected attempt doesn't consume quota
            raise PlanLimitExceeded(metric, limit)
    except PlanLimitExceeded:
        raise
    except Exception as e:
        log.warning("redis limiter unavailable (%r); falling back to PostgreSQL", e)
        await pg_check_and_increment(db, user, metric)
        return

    # PG writeback as statistics: sync every Nth increment to keep history
    # without a transaction per message.
    every = get_settings().usage_pg_writeback_every
    if every > 0 and value % every == 0:
        try:
            await _writeback(db, user, metric, day, value)
        except Exception:  # statistics must never fail the request
            log.warning("usage writeback failed", exc_info=True)


async def _writeback(db: AsyncSession, user: User, metric: str, day: str, value: int) -> None:
    from sqlalchemy import select

    from app.models import UsageCounter

    row = await db.execute(
        select(UsageCounter).where(
            UsageCounter.tenant_id == user.tenant_id,
            UsageCounter.user_id == user.id,
            UsageCounter.day == day,
            UsageCounter.metric == metric,
        )
    )
    counter = row.scalar_one_or_none()
    if counter is None:
        counter = UsageCounter(tenant_id=user.tenant_id, user_id=user.id, day=day, metric=metric, value=value)
        db.add(counter)
    else:
        counter.value = max(counter.value, value)
    await db.flush()


async def hit_ip_limit(ip: str, scope: str = "auth") -> bool:
    """Fixed-window per-IP limiter. Returns True when the request must be
    rejected (429). Fails open: Redis trouble never blocks logins."""
    settings = get_settings()
    limit = settings.auth_rate_limit_per_minute
    if limit <= 0 or not ip:
        return False
    key = f"ratelimit:{scope}:{ip}"
    try:
        redis = get_redis()
        value = await redis.incr(key)
        if value == 1:
            await redis.expire(key, 60)
        return value > limit
    except Exception:
        return False
