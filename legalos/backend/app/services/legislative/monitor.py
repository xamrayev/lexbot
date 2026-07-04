"""Legislative Intelligence: track Lex.uz / Norma.uz acts and their revisions.

For each tracked act we fetch the current text, hash it, and if the hash
differs from the latest stored revision we: store a new immutable revision,
re-chunk and re-embed the text into the shared legislation tenant, and publish
a "legislation.changed" event to RabbitMQ so subscribed users get notified and
the Knowledge Graph updater runs.
"""

import hashlib
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ComplianceWatch, DocumentChunk, LegislativeAct, LegislativeRevision, Notification
from app.services.documents.ingest import split_into_chunks
from app.services.ai.registry import get_embedding_provider
from app.services.rag.retrieval import LEGISLATION_TENANT_ID


async def fetch_act_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def reindex_act(db: AsyncSession, act: LegislativeAct, text: str) -> None:
    """Replace the act's chunks in the shared legislation tenant."""
    await db.execute(delete(DocumentChunk).where(DocumentChunk.act_id == act.id))
    chunk_texts = split_into_chunks(text)
    try:
        embeddings: list[list[float] | None] = list(await get_embedding_provider().embed(chunk_texts))
    except Exception:
        embeddings = [None] * len(chunk_texts)
    for seq, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                tenant_id=LEGISLATION_TENANT_ID,
                act_id=act.id,
                seq=seq,
                text=chunk_text,
                embedding=embedding,
                meta={"title": act.title, "url": act.url, "act_id": str(act.id), "source": act.source},
            )
        )


async def check_act_for_changes(db: AsyncSession, act: LegislativeAct) -> bool:
    """Returns True if a new revision was detected and stored."""
    text = await fetch_act_text(act.url)
    digest = content_hash(text)
    act.last_checked_at = datetime.now(timezone.utc)

    row = await db.execute(
        select(LegislativeRevision)
        .where(LegislativeRevision.act_id == act.id)
        .order_by(LegislativeRevision.revision.desc())
        .limit(1)
    )
    latest = row.scalar_one_or_none()
    if latest is not None and latest.content_hash == digest:
        return False

    act.current_revision = (latest.revision + 1) if latest else 1
    db.add(
        LegislativeRevision(
            act_id=act.id,
            revision=act.current_revision,
            content_hash=digest,
            text=text,
        )
    )
    await reindex_act(db, act, text)
    await notify_watchers(db, act)
    await db.flush()
    return True


async def notify_watchers(db: AsyncSession, act: LegislativeAct) -> None:
    """Create in-app notifications for every tenant watching this act (Compliance Center)."""
    rows = await db.execute(select(ComplianceWatch.tenant_id).where(ComplianceWatch.act_id == act.id).distinct())
    for tenant_id in rows.scalars():
        db.add(
            Notification(
                tenant_id=tenant_id,
                kind="legislation.changed",
                title=f"Изменение законодательства: {act.title[:400]}",
                body=f"Обнаружена новая редакция №{act.current_revision}. Проверьте влияние на документы организации.",
                meta={"act_id": str(act.id), "revision": act.current_revision, "url": act.url},
            )
        )
