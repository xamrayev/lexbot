"""End-to-end RAG pipeline: hybrid retrieval → rerank → cited context.

Knowledge-graph expansion is exposed as a hook so the existing Neo4j GraphRAG
(see repository root ``backend/``) or a future pg-based graph can be plugged in
without touching callers.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_embedding_provider, get_provider
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


async def _llm_rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Cheap listwise LLM reranker. Falls back to fusion order on any failure."""
    if len(chunks) <= top_k:
        return chunks
    numbered = "\n\n".join(f"[{i}] {c.text[:500]}" for i, c in enumerate(chunks))
    prompt = (
        "You rank text fragments by relevance to a legal question.\n"
        f"Question: {query}\n\nFragments:\n{numbered}\n\n"
        f"Return the indices of the {top_k} most relevant fragments, "
        "comma-separated, most relevant first. Answer with indices only."
    )
    try:
        result = await get_provider().complete([ChatMessage(role="user", content=prompt)], max_tokens=100)
        indices = [int(tok) for tok in result.content.replace(" ", "").split(",") if tok.strip().isdigit()]
        picked = [chunks[i] for i in indices if 0 <= i < len(chunks)]
        return picked[:top_k] if picked else chunks[:top_k]
    except Exception:
        return chunks[:top_k]


async def retrieve(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    *,
    top_k: int = 6,
    use_reranker: bool = True,
    graph_expander=None,
) -> RAGResult:
    from app.core.config import get_settings
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
    rerank_enabled = use_reranker and get_settings().rag_reranker == "llm"
    top = await _llm_rerank(query, fused[: top_k * 4], top_k) if rerank_enabled else fused[:top_k]

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
