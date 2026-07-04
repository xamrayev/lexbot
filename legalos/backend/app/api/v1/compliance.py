"""Compliance Center API (Enterprise / Government tiers).

- watch/unwatch legislative acts → notifications when a watched act changes
- run an LLM compliance check on an uploaded document
- read notifications
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.db.base import get_db
from app.models import ComplianceCheck, ComplianceWatch, Document, LegislativeAct, Notification, User
from app.services.billing.plans import get_tenant_plan
from app.services.compliance.checker import run_document_check

router = APIRouter(prefix="/compliance", tags=["compliance"])


async def require_compliance_plan(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    plan = await get_tenant_plan(db, user.tenant_id)
    if "compliance" not in plan.agents:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Compliance Center requires the Enterprise plan (current: {plan.tier.value})",
        )
    return user


@router.get("/watches")
async def list_watches(user: User = Depends(require_compliance_plan), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(ComplianceWatch, LegislativeAct.title, LegislativeAct.url)
        .join(LegislativeAct, LegislativeAct.id == ComplianceWatch.act_id)
        .where(ComplianceWatch.tenant_id == user.tenant_id)
    )
    return [
        {"act_id": str(watch.act_id), "title": title, "url": url, "since": watch.created_at.isoformat()}
        for watch, title, url in rows
    ]


@router.put("/watches/{act_id}", status_code=status.HTTP_204_NO_CONTENT)
async def watch_act(
    act_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_compliance_plan),
    db: AsyncSession = Depends(get_db),
):
    act = (await db.execute(select(LegislativeAct).where(LegislativeAct.id == act_id))).scalar_one_or_none()
    if act is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Act not found")
    existing = await db.execute(
        select(ComplianceWatch).where(
            ComplianceWatch.tenant_id == user.tenant_id, ComplianceWatch.act_id == act_id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(ComplianceWatch(tenant_id=user.tenant_id, act_id=act_id, created_by=user.id))
        await write_audit(db, request, user, "compliance.watch", resource=str(act_id))
        await db.commit()


@router.delete("/watches/{act_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unwatch_act(
    act_id: uuid.UUID,
    user: User = Depends(require_compliance_plan),
    db: AsyncSession = Depends(get_db),
):
    watch = (
        await db.execute(
            select(ComplianceWatch).where(
                ComplianceWatch.tenant_id == user.tenant_id, ComplianceWatch.act_id == act_id
            )
        )
    ).scalar_one_or_none()
    if watch is not None:
        await db.delete(watch)
        await db.commit()


@router.post("/checks/{document_id}")
async def check_document(
    document_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_compliance_plan),
    db: AsyncSession = Depends(get_db),
):
    document = (
        await db.execute(
            select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    check = await run_document_check(db, document=document, requested_by=user.id)
    await write_audit(db, request, user, "compliance.check", resource=str(document_id))
    await db.commit()
    return {
        "check_id": str(check.id),
        "document_id": str(document_id),
        "status": check.status,
        "findings": check.findings,
    }


@router.get("/checks")
async def list_checks(user: User = Depends(require_compliance_plan), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(ComplianceCheck)
        .where(ComplianceCheck.tenant_id == user.tenant_id)
        .order_by(ComplianceCheck.created_at.desc())
        .limit(100)
    )
    return [
        {
            "check_id": str(c.id),
            "document_id": str(c.document_id),
            "status": c.status,
            "findings": c.findings,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows.scalars()
    ]


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.tenant_id == user.tenant_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    rows = await db.execute(stmt.order_by(Notification.created_at.desc()).limit(100))
    return [
        {
            "id": str(n.id),
            "kind": n.kind,
            "title": n.title,
            "body": n.body,
            "meta": n.meta,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows.scalars()
    ]


@router.post("/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification).where(Notification.tenant_id == user.tenant_id).values(is_read=True)
    )
    await db.commit()
