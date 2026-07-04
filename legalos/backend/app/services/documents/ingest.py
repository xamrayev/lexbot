"""Document Intelligence: conversion, chunking, classification, indexing.

Conversion uses IBM Docling when installed (PDF/DOCX/XLSX/HTML/Markdown + OCR
+ table extraction); plain-text decode is the fallback so the pipeline degrades
gracefully in minimal environments.
"""

import io
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_embedding_provider, get_provider

CHUNK_SIZE = 1600  # characters, ~400 tokens
CHUNK_OVERLAP = 200

CATEGORIES = ["employment_contract", "order", "policy", "letter", "accounting", "contract", "other"]


def convert_to_text(filename: str, content: bytes, mime_type: str) -> str:
    """Convert an uploaded file to plain text/markdown via Docling if available."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore

        converter = DocumentConverter()
        result = converter.convert(io.BytesIO(content))
        return result.document.export_to_markdown()
    except ImportError:
        pass
    except Exception:
        pass
    # Fallback: best-effort UTF-8 decode (txt, md, html, email)
    return content.decode("utf-8", errors="replace")


def split_into_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


async def classify_document(text: str) -> str:
    """LLM zero-shot classification into a fixed category set."""
    prompt = (
        "Classify this document into exactly one category from: "
        f"{', '.join(CATEGORIES)}.\n\nDocument excerpt:\n{text[:2000]}\n\n"
        "Answer with the category slug only."
    )
    try:
        result = await get_provider().complete([ChatMessage(role="user", content=prompt)], max_tokens=10)
        category = result.content.strip().lower()
        return category if category in CATEGORIES else "other"
    except Exception:
        return "other"


async def index_document(db: AsyncSession, document: Document, text: str) -> int:
    """Chunk, embed, and store a document. Returns the number of chunks."""
    chunk_texts = split_into_chunks(text)
    embeddings: list[list[float] | None]
    try:
        embeddings = list(await get_embedding_provider().embed(chunk_texts))
    except Exception:
        embeddings = [None] * len(chunk_texts)  # BM25-only until reindexed

    for seq, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                tenant_id=document.tenant_id,
                document_id=document.id,
                seq=seq,
                text=chunk_text,
                embedding=embedding,
                meta={"title": document.title, "document_id": str(document.id), "category": document.category},
            )
        )
    document.status = "ready"
    await db.flush()
    return len(chunk_texts)
