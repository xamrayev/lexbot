"""Shared async Redis client (lazy singleton).

Redis backs rate limiting, usage counters and the refresh-token denylist.
Callers must treat Redis as optional infrastructure: wrap calls and fall back
gracefully — an unavailable Redis must never take the API down.
"""

from redis.asyncio import Redis

from app.core.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
    return _client


def set_redis(client: Redis | None) -> None:
    """Test hook: inject a fake client (fakeredis) or reset the singleton."""
    global _client
    _client = client
