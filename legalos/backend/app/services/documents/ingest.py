"""Document Intelligence: conversion, chunking, classification, indexing.

Conversion uses IBM Docling when installed (PDF/DOCX/XLSX/HTML/Markdown + OCR
+ table extraction); plain-text decode is the fallback so the pipeline degrades
gracefully in minimal environments.
"""

import io
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_embedding_provider, get_provider

CHUNK_SIZE = 1600  # characters, ~400 tokens
CHUNK_OVERLAP = 200

CATEGORIES = ["employment_contract", "order", "policy", "letter", "accounting", "contract", "other"]

_HEADING = re.compile(r"^#{1,6}\s+(?P<title>.+)$")
_SENTENCE_END = re.compile(r"(?<=[.!?…:;])\s+")


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


def _split_units(paragraph: str) -> list[str]:
    """Sentences of a paragraph; any unit longer than CHUNK_SIZE is hard-wrapped."""
    units: list[str] = []
    for sentence in _SENTENCE_END.split(paragraph):
        sentence = sentence.strip()
        while len(sentence) > CHUNK_SIZE:
            units.append(sentence[:CHUNK_SIZE])
            sentence = sentence[CHUNK_SIZE:]
        if sentence:
            units.append(sentence)
    return units


def structured_chunks(text: str) -> list[dict]:
    """Structure-aware chunking: ``{"text": str, "section": str}``.

    Packing respects paragraph (blank line) and sentence boundaries — a
    sentence is never cut mid-way unless it alone exceeds CHUNK_SIZE.
    Markdown headings (Docling output) start a new chunk and become the
    chunk's ``section``; overlap between size-split chunks is the trailing
    sentences of the previous chunk (up to CHUNK_OVERLAP chars) so a thought
    crossing the boundary stays intact in one of them.
    """
    chunks: list[dict] = []
    section = ""
    buffer: list[str] = []
    buffer_len = 0

    def flush(carry_overlap: bool) -> None:
        nonlocal buffer, buffer_len
        if not buffer:
            return
        chunks.append({"text": "\n".join(buffer).strip(), "section": section})
        if carry_overlap:
            overlap: list[str] = []
            size = 0
            for unit in reversed(buffer):
                if size + len(unit) > CHUNK_OVERLAP:
                    break
                overlap.insert(0, unit)
                size += len(unit) + 1
            buffer = overlap
            buffer_len = size
        else:
            buffer = []
            buffer_len = 0

    for raw_paragraph in text.split("\n\n"):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        for line_or_unit in paragraph.splitlines():
            heading = _HEADING.match(line_or_unit.strip())
            if heading:
                flush(carry_overlap=False)  # sections don't bleed into each other
                section = heading.group("title").strip()
                buffer = [line_or_unit.strip()]
                buffer_len = len(line_or_unit)
                continue
            for unit in _split_units(line_or_unit):
                if buffer_len + len(unit) > CHUNK_SIZE:
                    flush(carry_overlap=True)
                buffer.append(unit)
                buffer_len += len(unit) + 1
    flush(carry_overlap=False)
    return [c for c in chunks if c["text"]]


def split_into_chunks(text: str) -> list[str]:
    return [chunk["text"] for chunk in structured_chunks(text)]


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
    """Chunk (structure-aware), embed, and store a document. Returns the chunk count."""
    chunks = structured_chunks(text)
    embeddings: list[list[float] | None]
    try:
        embeddings = list(await get_embedding_provider().embed([c["text"] for c in chunks]))
    except Exception:
        embeddings = [None] * len(chunks)  # BM25-only until reindexed

    for seq, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        meta = {"title": document.title, "document_id": str(document.id), "category": document.category}
        if chunk["section"]:
            meta["section"] = chunk["section"]
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                tenant_id=document.tenant_id,
                document_id=document.id,
                seq=seq,
                text=chunk["text"],
                embedding=embedding,
                meta=meta,
            )
        )
    document.status = "ready"
    await db.flush()
    return len(chunks)
