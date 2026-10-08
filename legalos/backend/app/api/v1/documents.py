"""Document upload → MinIO storage → Docling conversion → classification → indexing."""

import uuid

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.core.config import get_settings
from app.db.base import get_db
from app.models import Document, User
from app.schemas import DocumentOut, GenerateDocumentRequest
from app.services.billing.limiter import check_and_increment_redis as check_and_increment
from app.services.billing.plans import PlanLimitExceeded, get_tenant_plan
from app.services.documents.generate import DOC_TYPES, generate_document
from app.services.documents.ingest import classify_document, convert_to_text, index_document
from app.services.documents.pdf import build_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _store_in_minio(key: str, content: bytes, mime_type: str) -> None:
    import io

    from minio import Minio

    s = get_settings()
    client = Minio(s.minio_endpoint, access_key=s.minio_access_key, secret_key=s.minio_secret_key, secure=s.minio_secure)
    if not client.bucket_exists(s.minio_bucket):
        client.make_bucket(s.minio_bucket)
    client.put_object(s.minio_bucket, key, io.BytesIO(content), len(content), content_type=mime_type)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_tenant_plan(db, user.tenant_id)
    if not plan.document_upload:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Document upload requires HR Pro or higher")
    try:
        await check_and_increment(db, user, "documents")
    except PlanLimitExceeded as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e))

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 50 MB limit")

    mime_type = file.content_type or "application/octet-stream"
    doc_id = uuid.uuid4()
    storage_key = f"{user.tenant_id}/{doc_id}/{file.filename}"
    try:
        _store_in_minio(storage_key, content, mime_type)
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Object storage unavailable: {e}")

    document = Document(
        id=doc_id,
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        title=file.filename or "untitled",
        storage_key=storage_key,
        mime_type=mime_type,
        status="indexing",
    )
    db.add(document)
    await db.flush()

    # Synchronous ingestion; a RabbitMQ worker handles large batches (see app/workers).
    text = convert_to_text(file.filename or "", content, mime_type)
    document.category = await classify_document(text)
    await index_document(db, document, text)
    await write_audit(db, request, user, "document.upload", resource=str(doc_id))
    await db.commit()
    return document


@router.get("/generate/types")
async def list_document_types(user: User = Depends(get_current_user)):
    return [{"slug": slug, "name": name} for slug, name in DOC_TYPES.items()]


@router.post("/generate")
async def generate(
    body: GenerateDocumentRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an HR/legal document (grounded in legislation) and return it as DOCX.

    Available on every tier — document generation is part of the Free HR
    Assistant — but counts against the daily message quota.
    """
    try:
        await check_and_increment(db, user, "messages")
    except PlanLimitExceeded as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e))
    try:
        generated = await generate_document(
            db, user.tenant_id, doc_type=body.doc_type, instructions=body.instructions, provider_name=body.provider
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    await write_audit(
        db, request, user, "document.generate", detail={"doc_type": body.doc_type, "format": body.format}
    )
    await db.commit()

    if body.format == "pdf":
        payload = build_pdf(generated.text)
        media_type = "application/pdf"
    else:
        payload = generated.docx
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = quote(f"{generated.title[:60]}.{body.format}")
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "X-Document-Title": quote(generated.title),
        },
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Document).where(Document.tenant_id == user.tenant_id).order_by(Document.created_at.desc()).limit(200)
    )
    return list(rows.scalars())


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
    )
    document = row.scalar_one_or_none()
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document
