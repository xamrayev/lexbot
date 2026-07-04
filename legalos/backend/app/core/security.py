"""JWT + password hashing utilities (OAuth2 password flow compatible)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, tenant_id: str | None, token_type: str, expires_delta: timedelta) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, tenant_id: str | None = None) -> str:
    settings = get_settings()
    return _create_token(user_id, tenant_id, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: str, tenant_id: str | None = None) -> str:
    settings = get_settings()
    return _create_token(user_id, tenant_id, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
