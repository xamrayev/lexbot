"""Seed the shared legislation knowledge base with the Uzbek Labor Code.

Loads a processed dataset (data/mehnat_kodeksi_processed.json — one chunk per
article with modda/bob metadata) into the legislation tenant: creates the
LegislativeAct + revision 1 and one DocumentChunk per article. Embeddings are
computed when an embedding provider is configured; otherwise chunks are
searchable via BM25 immediately and can be re-embedded later.

Usage (inside the backend container or venv):
    python -m app.scripts.seed_labor_code /path/to/mehnat_kodeksi_processed.json
"""

import asyncio
import hashlib
import json
import sys
import uuid

from sqlalchemy import delete, select, text as sql_text

from app.db.base import Base, async_session_factory, engine
from app.models import DocumentChunk, LegislativeAct, LegislativeRevision, Tenant
from app.services.ai.registry import get_embedding_provider
from app.services.rag.retrieval import LEGISLATION_TENANT_ID

ACT_EXTERNAL_ID = "lex.uz/docs/6257288"  # Labor Code of the Republic of Uzbekistan (2022)
ACT_URL = "https://lex.uz/docs/6257288"
EMBED_BATCH = 64


def parse_dataset(raw: dict) -> tuple[str, list[dict]]:
    """Extract (act title, chunk dicts) from the processed dataset. Pure — unit-testable."""
    title = raw.get("metadata", {}).get("code_name", "O'zbekiston Respublikasining Mehnat kodeksi")
    chunks = []
    for chunk in raw["chunks"]:
        meta = chunk.get("metadata", {})
        chunks.append(
            {
                "text": chunk["text"],
                "meta": {
                    "title": title,
                    "url": ACT_URL,
                    "article": meta.get("modda_number", ""),
                    "article_title": meta.get("modda_title", ""),
                    "chapter": meta.get("bob_title", ""),
                    "hierarchy": meta.get("hierarchy", ""),
                    "language": meta.get("language", "uz"),
                    "source": "lex.uz",
                },
            }
        )
    return title, chunks


async def _embed_all(texts: list[str]) -> list[list[float] | None]:
    provider = get_embedding_provider()
    vectors: list[list[float] | None] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        try:
            vectors.extend(await provider.embed(batch))
        except Exception as e:
            print(f"  embeddings unavailable ({e!r}) — continuing with BM25-only chunks", file=sys.stderr)
            vectors.extend([None] * (len(texts) - len(vectors)))
            break
    return vectors


async def seed(dataset_path: str) -> None:
    with open(dataset_path, encoding="utf-8") as f:
        raw = json.load(f)
    title, chunks = parse_dataset(raw)
    full_text = "\n\n".join(c["text"] for c in chunks)

    async with engine.begin() as conn:
        await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Well-known tenant that owns shared legislative content
        tenant = (await db.execute(select(Tenant).where(Tenant.id == LEGISLATION_TENANT_ID))).scalar_one_or_none()
        if tenant is None:
            db.add(Tenant(id=LEGISLATION_TENANT_ID, name="Legislation (shared)", slug="legislation"))
            await db.flush()

        act = (
            await db.execute(select(LegislativeAct).where(LegislativeAct.external_id == ACT_EXTERNAL_ID))
        ).scalar_one_or_none()
        if act is None:
            act = LegislativeAct(
                source="lex.uz",
                external_id=ACT_EXTERNAL_ID,
                title=title,
                url=ACT_URL,
                act_type="code",
                current_revision=1,
            )
            db.add(act)
            await db.flush()
            db.add(
                LegislativeRevision(
                    act_id=act.id,
                    revision=1,
                    content_hash=hashlib.sha256(full_text.encode()).hexdigest(),
                    text=full_text,
                )
            )
        else:
            print(f"act already tracked (id={act.id}); replacing its chunks")

        await db.execute(delete(DocumentChunk).where(DocumentChunk.act_id == act.id))

        print(f"embedding {len(chunks)} article chunks…")
        vectors = await _embed_all([c["text"] for c in chunks])
        for seq, (chunk, vector) in enumerate(zip(chunks, vectors)):
            db.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    tenant_id=LEGISLATION_TENANT_ID,
                    act_id=act.id,
                    seq=seq,
                    text=chunk["text"],
                    embedding=vector,
                    meta={**chunk["meta"], "act_id": str(act.id)},
                )
            )
        await db.commit()
        embedded = sum(1 for v in vectors if v is not None)
        print(f"done: {len(chunks)} chunks stored ({embedded} with embeddings) for '{title}'")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(seed(sys.argv[1]))
