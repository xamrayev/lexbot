"""Reranking strategies for Hybrid Search results.

Selected by LEGALOS_RAG_RERANKER:
- ``llm``           — listwise reranking by the default chat model (no extra infra);
- ``cross_encoder`` — local sentence-transformers CrossEncoder
  (LEGALOS_CROSS_ENCODER_MODEL, optional heavy dependency); more accurate and
  cheaper per query at scale, requires the model to be installed/downloaded;
- ``none``          — keep reciprocal-rank-fusion order.

Every strategy degrades to fusion order on failure — reranking must never
break retrieval.
"""

import asyncio
import logging

from app.core.config import get_settings
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_provider
from app.services.rag.retrieval import RetrievedChunk

log = logging.getLogger("legalos.rag.rerankers")

_cross_encoder = None  # lazy singleton — model load is expensive


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


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder  # optional dependency

        _cross_encoder = CrossEncoder(get_settings().cross_encoder_model)
    return _cross_encoder


async def _cross_encoder_rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if len(chunks) <= top_k:
        return chunks
    try:
        model = await asyncio.to_thread(_get_cross_encoder)
        scores = await asyncio.to_thread(model.predict, [(query, c.text[:1500]) for c in chunks])
        ranked = sorted(zip(chunks, scores), key=lambda pair: float(pair[1]), reverse=True)
        return [chunk for chunk, _ in ranked[:top_k]]
    except Exception as e:
        log.warning("cross-encoder rerank unavailable (%r); falling back to fusion order", e)
        return chunks[:top_k]


async def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Apply the configured reranking strategy."""
    mode = get_settings().rag_reranker
    if mode == "llm":
        return await _llm_rerank(query, chunks, top_k)
    if mode == "cross_encoder":
        return await _cross_encoder_rerank(query, chunks, top_k)
    return chunks[:top_k]
