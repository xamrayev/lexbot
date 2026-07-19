"""Refresh-token denylist (rotation + revocation).

Every refresh use rotates the token: the old ``jti`` goes onto the denylist
for the remainder of its TTL, and a reused (stolen or replayed) refresh token
is rejected. Redis is the primary store; a bounded in-process fallback keeps
revocation working in single-instance dev setups without Redis.
"""

import logging
import time

from app.core.redis import get_redis

log = logging.getLogger("legalos.tokens")

_KEY = "revoked:refresh:"
# In-process fallback: jti -> expiry timestamp. Only effective within one
# process — production revocation requires Redis.
_local: dict[str, float] = {}
_LOCAL_MAX = 10_000


def _local_cleanup() -> None:
    now = time.time()
    for jti in [j for j, exp in _local.items() if exp < now]:
        _local.pop(jti, None)
    while len(_local) > _LOCAL_MAX:
        _local.pop(next(iter(_local)), None)


async def revoke(jti: str, ttl_seconds: int) -> None:
    if not jti or ttl_seconds <= 0:
        return
    try:
        await get_redis().setex(_KEY + jti, ttl_seconds, "1")
    except Exception as e:
        log.warning("redis denylist unavailable (%r); using in-process fallback", e)
        _local_cleanup()
        _local[jti] = time.time() + ttl_seconds


async def is_revoked(jti: str) -> bool:
    if not jti:
        return True  # tokens minted before jti was introduced can't be rotated safely
    try:
        if await get_redis().exists(_KEY + jti):
            return True
    except Exception:
        pass
    return _local.get(jti, 0) > time.time()
