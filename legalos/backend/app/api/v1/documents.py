"""Document upload → MinIO storage → Docling conversion → classification → indexing."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, write_audit
from app.core.config import get_settings
from app.db.base import get_db
from app.models import Document, User
from app.schemas import DocumentOut
from app.services.billing.plans import PlanLimitExceeded, check_and_increment, get_tenant_plan
from app.services.documents.ingest import classify_document, convert_to_text, index_document

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
