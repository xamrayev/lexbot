"""SSO endpoints: GET /auth/sso/login → IdP, GET /auth/sso/callback → JWT."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import write_audit
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.base import get_db
from app.models import PlanTier, Subscription, Tenant, User, UserRole
from app.schemas import TokenResponse
from app.services.sso.oidc import SSONotConfigured, build_authorization_url, exchange_code, verify_state

router = APIRouter(prefix="/auth/sso", tags=["auth"])


async def _get_or_create_sso_tenant(db: AsyncSession) -> Tenant:
    settings = get_settings()
    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == settings.sso_tenant_slug))
    ).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=f"SSO — {settings.app_name}", slug=settings.sso_tenant_slug)
        db.add(tenant)
        await db.flush()
        # SSO is an Enterprise feature, so the SSO tenant gets the Enterprise tier.
        db.add(Subscription(tenant_id=tenant.id, tier=PlanTier.enterprise))
    return tenant


async def provision_sso_user(db: AsyncSession, claims: dict) -> User:
    """Find or JIT-create the user matching the IdP's email claim."""
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Identity provider returned no email claim")

    tenant = await _get_or_create_sso_tenant(db)
    user = (
        await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == email))
    ).scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
        return user

    if not get_settings().sso_auto_provision:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not provisioned for SSO access")
    user = User(
        tenant_id=tenant.id,
        email=email,
        full_name=claims.get("name", ""),
        # SSO users never authenticate with a password; store an unguessable one.
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        role=UserRole.member,
    )
    db.add(user)
    await db.flush()
    return user


@router.get("/login")
async def sso_login():
    try:
        url, _state = await build_authorization_url()
    except SSONotConfigured as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(e))
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/callback", response_model=TokenResponse)
async def sso_callback(code: str, state: str, request: Request, db: AsyncSession = Depends(get_db)):
    if not verify_state(state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired state parameter")
    try:
        claims = await exchange_code(code)
    except SSONotConfigured as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(e))
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Identity provider exchange failed")

    user = await provision_sso_user(db, claims)
    await write_audit(db, request, user, "auth.sso_login")
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id)),
        refresh_token=create_refresh_token(str(user.id), str(user.tenant_id)),
    )
