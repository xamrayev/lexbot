"""Hybrid retrieval primitives: BM25 (PostgreSQL full-text), vector (pgvector),
and reciprocal-rank fusion of both result lists.

All queries are tenant-scoped: a chunk is visible if it belongs to the caller's
tenant (corporate documents) or is public legislation (act_id set, tenant_id of
the shared legislation tenant). This is the RAG-security boundary.
"""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

# Well-known tenant that owns shared legislative content (Lex.uz, Norma.uz).
LEGISLATION_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    meta: dict
    origin: str  # "bm25" | "vector" | "fused"


def to_or_tsquery(query: str, max_terms: int = 32) -> str:
    """Natural-language question → OR tsquery string ("sinov | muddati | ...").

    plainto_tsquery joins words with AND, so a question containing any word
    absent from the document ("qancha?", "сколько?") matches nothing.
    OR semantics lets ts_rank_cd rank by how many terms match instead.
    Tokens come from \\w+ so the result is safe tsquery syntax.
    """
    words = re.findall(r"\w+", query.lower())
    return " | ".join(dict.fromkeys(words[:max_terms]))  # de-dup, keep order


async def bm25_search(db: AsyncSession, tenant_id: uuid.UUID, query: str, limit: int = 20) -> list[RetrievedChunk]:
    tsquery = to_or_tsquery(query)
    if not tsquery:
        return []
    stmt = sql_text(
        """
        SELECT id, text, meta,
               ts_rank_cd(to_tsvector('simple', text), to_tsquery('simple', :q)) AS score
        FROM document_chunks
        WHERE tenant_id IN (:tenant_id, :legal_tenant)
          AND to_tsvector('simple', text) @@ to_tsquery('simple', :q)
        ORDER BY score DESC
        LIMIT :limit
        """
    )
    rows = await db.execute(
        stmt, {"q": tsquery, "tenant_id": tenant_id, "legal_tenant": LEGISLATION_TENANT_ID, "limit": limit}
    )
    return [
        RetrievedChunk(chunk_id=str(r.id), text=r.text, score=float(r.score), meta=r.meta or {}, origin="bm25")
        for r in rows
    ]


async def vector_search(
    db: AsyncSession, tenant_id: uuid.UUID, embedding: list[float], limit: int = 20
) -> list[RetrievedChunk]:
    stmt = sql_text(
        """
        SELECT id, text, meta, 1 - (embedding <=> CAST(:emb AS vector)) AS score
        FROM document_chunks
        WHERE tenant_id IN (:tenant_id, :legal_tenant) AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :limit
        """
    )
    rows = await db.execute(
        stmt,
        {
            "emb": str(embedding),
            "tenant_id": tenant_id,
            "legal_tenant": LEGISLATION_TENANT_ID,
            "limit": limit,
        },
    )
    return [
        RetrievedChunk(chunk_id=str(r.id), text=r.text, score=float(r.score), meta=r.meta or {}, origin="vector")
        for r in rows
    ]


def reciprocal_rank_fusion(result_lists: list[list[RetrievedChunk]], k: int = 60) -> list[RetrievedChunk]:
    """Standard RRF: robust fusion of heterogeneous score scales."""
    fused: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    for results in result_lists:
        for rank, chunk in enumerate(results):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            fused.setdefault(chunk.chunk_id, chunk)
    ranked = sorted(fused.values(), key=lambda c: scores[c.chunk_id], reverse=True)
    return [
        RetrievedChunk(chunk_id=c.chunk_id, text=c.text, score=scores[c.chunk_id], meta=c.meta, origin="fused")
        for c in ranked
    ]
