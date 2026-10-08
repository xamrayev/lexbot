"""End-to-end RAG pipeline: hybrid retrieval → rerank → cited context.

Knowledge-graph expansion is exposed as a hook so the existing Neo4j GraphRAG
(see repository root ``backend/``) or a future pg-based graph can be plugged in
without touching callers.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.registry import get_embedding_provider
from app.services.rag.rerankers import rerank
from app.services.rag.retrieval import (
    RetrievedChunk,
    bm25_search,
    reciprocal_rank_fusion,
    vector_search,
)


@dataclass
class RAGResult:
    context: str
    sources: list[dict] = field(default_factory=list)


async def retrieve(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    *,
    top_k: int = 6,
    use_reranker: bool = True,
    graph_expander=None,
) -> RAGResult:
    from app.services.rag.graph import get_default_graph_expander

    embedding_provider = get_embedding_provider()
    try:
        query_embedding = (await embedding_provider.embed([query]))[0]
        vector_hits = await vector_search(db, tenant_id, query_embedding)
    except Exception:
        vector_hits = []  # degrade gracefully to lexical-only search
    bm25_hits = await bm25_search(db, tenant_id, query)

    fused = reciprocal_rank_fusion([bm25_hits, vector_hits])
    expander = graph_expander if graph_expander is not None else get_default_graph_expander()
    if expander is not None:
        fused = await expander(db, tenant_id, query, fused)
    top = await rerank(query, fused[: top_k * 4], top_k) if use_reranker else fused[:top_k]

    sources = [
        {
            "chunk_id": c.chunk_id,
            "score": round(c.score, 4),
            "excerpt": c.text[:300],
            **{k: c.meta[k] for k in ("title", "url", "article", "document_id", "act_id") if k in c.meta},
        }
        for c in top
    ]
    context = "\n\n---\n\n".join(f"[Source {i + 1}] {c.text}" for i, c in enumerate(top))
    return RAGResult(context=context, sources=sources)
