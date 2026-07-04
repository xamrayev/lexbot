"""Registration + OAuth2 password login issuing JWT access/refresh tokens."""

import re
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.base import get_db
from app.models import PlanTier, Subscription, Tenant, User, UserRole
from app.schemas import RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:12]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    org_name = body.organization or f"Personal — {body.email}"
    slug = _slugify(org_name)
    exists = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if exists.scalar_one_or_none() is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    tenant = Tenant(name=org_name, slug=slug)
    db.add(tenant)
    await db.flush()

    email_taken = await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == body.email))
    if email_taken.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=UserRole.owner,
    )
    db.add(user)
    db.add(Subscription(tenant_id=tenant.id, tier=PlanTier.free))
    await db.flush()
    await write_audit(db, request, user, "auth.register")
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(tenant.id)),
        refresh_token=create_refresh_token(str(user.id), str(tenant.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(select(User).where(User.email == form.username, User.is_active.is_(True)))
    user = row.scalars().first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    await write_audit(db, request, user, "auth.login")
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id)),
        refresh_token=create_refresh_token(str(user.id), str(user.tenant_id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except pyjwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    row = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"]), User.is_active.is_(True)))
    user = row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id)),
        refresh_token=create_refresh_token(str(user.id), str(user.tenant_id)),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
