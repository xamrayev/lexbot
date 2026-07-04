"""RabbitMQ worker: async document indexing and scheduled legislative sync.

Queues:
  legalos.index        — {"document_id": "..."} re-index a stored document
  legalos.legislation  — {"act_id": "..."} check one act for changes

Run:  python -m app.workers.consumer
"""

import asyncio
import json
import logging
import uuid

import aio_pika
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import async_session_factory
from app.models import Document, LegislativeAct
from app.services.legislative.monitor import check_act_for_changes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("legalos.worker")

INDEX_QUEUE = "legalos.index"
LEGISLATION_QUEUE = "legalos.legislation"


async def handle_index(payload: dict) -> None:
    from minio import Minio

    from app.services.documents.ingest import classify_document, convert_to_text, index_document

    s = get_settings()
    async with async_session_factory() as db:
        row = await db.execute(select(Document).where(Document.id == uuid.UUID(payload["document_id"])))
        document = row.scalar_one_or_none()
        if document is None:
            log.warning("document %s not found", payload["document_id"])
            return
        client = Minio(s.minio_endpoint, access_key=s.minio_access_key, secret_key=s.minio_secret_key, secure=s.minio_secure)
        obj = client.get_object(s.minio_bucket, document.storage_key)
        try:
            content = obj.read()
        finally:
            obj.close()
            obj.release_conn()
        text = convert_to_text(document.title, content, document.mime_type)
        document.category = await classify_document(text)
        chunks = await index_document(db, document, text)
        await db.commit()
        log.info("indexed document %s (%d chunks)", document.id, chunks)


async def handle_legislation(payload: dict) -> None:
    async with async_session_factory() as db:
        row = await db.execute(select(LegislativeAct).where(LegislativeAct.id == uuid.UUID(payload["act_id"])))
        act = row.scalar_one_or_none()
        if act is None:
            return
        changed = await check_act_for_changes(db, act)
        await db.commit()
        log.info("act %s checked, changed=%s", act.title, changed)


HANDLERS = {INDEX_QUEUE: handle_index, LEGISLATION_QUEUE: handle_legislation}


async def main() -> None:
    connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=4)

    for queue_name, handler in HANDLERS.items():
        queue = await channel.declare_queue(queue_name, durable=True)

        async def consume(message: aio_pika.abc.AbstractIncomingMessage, handler=handler) -> None:
            async with message.process(requeue=False):
                try:
                    await handler(json.loads(message.body))
                except Exception:
                    log.exception("failed to process message on %s", message.routing_key)

        await queue.consume(consume)
        log.info("consuming %s", queue_name)

    await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
