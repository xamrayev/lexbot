"""Compliance Center: LLM review of corporate documents against legislation.

The model receives the document text plus retrieved legislation context and
returns structured findings. `parse_findings` is a pure function so response
parsing is unit-testable without an LLM.
"""

import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ComplianceCheck, Document, DocumentChunk
from app.services.ai.base import ChatMessage
from app.services.ai.registry import get_provider
from app.services.rag.pipeline import retrieve
from app.services.security.guard import wrap_retrieved_context

MAX_DOC_CHARS = 12_000
SEVERITIES = {"critical", "warning", "info"}

_SYSTEM_PROMPT = """Ты — комплаенс-офицер, проверяющий документы организации на соответствие
законодательству Республики Узбекистан.

Проанализируй документ и верни ТОЛЬКО JSON-массив замечаний (может быть пустым []):
[
  {
    "severity": "critical" | "warning" | "info",
    "issue": "краткое описание несоответствия",
    "recommendation": "как исправить",
    "article": "статья закона, если применимо"
  }
]
Не выдумывай нарушения: если документ корректен, верни []."""


def parse_findings(raw: str) -> list[dict]:
    """Extract and normalize the findings array from an LLM response."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    findings = []
    for item in data:
        if not isinstance(item, dict) or "issue" not in item:
            continue
        severity = str(item.get("severity", "info")).lower()
        findings.append(
            {
                "severity": severity if severity in SEVERITIES else "info",
                "issue": str(item["issue"]),
                "recommendation": str(item.get("recommendation", "")),
                "article": str(item.get("article", "")),
            }
        )
    return findings


async def _document_text(db: AsyncSession, document: Document) -> str:
    rows = await db.execute(
        select(DocumentChunk.text).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.seq)
    )
    return "\n".join(rows.scalars())[:MAX_DOC_CHARS]


async def run_document_check(
    db: AsyncSession,
    *,
    document: Document,
    requested_by: uuid.UUID,
    provider_name: str | None = None,
) -> ComplianceCheck:
    text = await _document_text(db, document)
    check = ComplianceCheck(
        tenant_id=document.tenant_id,
        document_id=document.id,
        requested_by=requested_by,
    )
    if not text.strip():
        check.status = "failed"
        check.findings = [{"severity": "info", "issue": "Документ не проиндексирован — текст недоступен",
                           "recommendation": "Дождитесь окончания индексации и повторите", "article": ""}]
        db.add(check)
        await db.flush()
        return check

    rag = await retrieve(db, document.tenant_id, text[:1500], top_k=5, use_reranker=False)
    messages = [ChatMessage(role="system", content=_SYSTEM_PROMPT)]
    if rag.context:
        messages.append(ChatMessage(role="system", content=wrap_retrieved_context(rag.context)))
    messages.append(ChatMessage(role="user", content=f"Документ «{document.title}»:\n\n{text}"))

    try:
        result = await get_provider(provider_name).complete(messages, temperature=0.0, max_tokens=2000)
        findings = parse_findings(result.content)
        check.findings = findings
        check.status = "issues" if findings else "ok"
    except Exception:
        check.status = "failed"
        check.findings = []
    db.add(check)
    await db.flush()
    return check
