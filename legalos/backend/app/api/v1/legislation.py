"""Legislative Intelligence API: tracked acts, revision history, manual sync."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.base import get_db
from app.models import LegislativeAct, LegislativeRevision, User, UserRole
from app.schemas import ActOut, TrackActRequest
from app.services.legislative.monitor import check_act_for_changes

router = APIRouter(prefix="/legislation", tags=["legislation"])


@router.get("/acts", response_model=list[ActOut])
async def list_acts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(LegislativeAct).order_by(LegislativeAct.title).limit(500))
    return list(rows.scalars())


@router.post("/acts", response_model=ActOut, status_code=status.HTTP_201_CREATED)
async def track_act(
    body: TrackActRequest,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    act = LegislativeAct(
        source=body.source,
        external_id=body.url,
        title=body.title,
        url=body.url,
        act_type=body.act_type,
        current_revision=0,
    )
    db.add(act)
    await db.commit()
    await db.refresh(act)
    return act


@router.post("/acts/{act_id}/sync")
async def sync_act(
    act_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(select(LegislativeAct).where(LegislativeAct.id == act_id))
    act = row.scalar_one_or_none()
    if act is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Act not found")
    changed = await check_act_for_changes(db, act)
    await db.commit()
    return {"act_id": str(act_id), "changed": changed, "current_revision": act.current_revision}


@router.get("/acts/{act_id}/revisions")
async def list_revisions(act_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(LegislativeRevision.revision, LegislativeRevision.content_hash, LegislativeRevision.created_at)
        .where(LegislativeRevision.act_id == act_id)
        .order_by(LegislativeRevision.revision.desc())
    )
    return [
        {"revision": r.revision, "content_hash": r.content_hash, "created_at": r.created_at.isoformat()}
        for r in rows
    ]
