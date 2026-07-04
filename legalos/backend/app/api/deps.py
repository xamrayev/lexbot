"""FastAPI dependencies: DB session, current user (JWT), RBAC, audit."""

import uuid

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.base import get_db
from app.models import AuditLog, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().api_v1_prefix}/auth/login")

_ROLE_ORDER = [UserRole.viewer, UserRole.member, UserRole.manager, UserRole.admin, UserRole.owner]


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired credentials")
    try:
        payload = decode_token(token)
    except pyjwt.PyJWTError:
        raise credentials_error
    if payload.get("type") != "access":
        raise credentials_error
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise credentials_error

    row = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_role(minimum: UserRole):
    """RBAC guard: allow only users whose role is >= `minimum`."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if _ROLE_ORDER.index(user.role) < _ROLE_ORDER.index(minimum):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


async def write_audit(
    db: AsyncSession,
    request: Request,
    user: User | None,
    action: str,
    resource: str = "",
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            action=action,
            resource=resource,
            detail=detail or {},
            ip_address=request.client.host if request.client else "",
        )
    )
