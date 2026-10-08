"""API integration tests against a real PostgreSQL (+pgvector).

Run only when LEGALOS_TEST_DATABASE_URL is set (CI provides a pgvector
service container; locally: docker run pgvector/pgvector:pg16). The app must
point at the same database, so set LEGALOS_DATABASE_URL to the same URL —
see .github/workflows/ci.yml.

Covered scenario: registration → login → /auth/me → plan gating (Free tier
cannot upload documents) → daily message quota → tenant isolation.
"""

import os
import uuid

import pytest

TEST_DB_URL = os.environ.get("LEGALOS_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="LEGALOS_TEST_DATABASE_URL is not set (integration tests need PostgreSQL+pgvector)",
)


@pytest.fixture(scope="module")
async def client():
    if os.environ.get("LEGALOS_DATABASE_URL") != TEST_DB_URL:
        pytest.skip("LEGALOS_DATABASE_URL must equal LEGALOS_TEST_DATABASE_URL for integration tests")

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text as sql_text

    from app.db.base import Base, engine
    from app.main import create_app

    async with engine.begin() as conn:
        await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    await engine.dispose()


def _creds(tag: str) -> dict:
    return {
        "email": f"user-{tag}-{uuid.uuid4().hex[:6]}@test.uz",
        "password": "secret-password-123",
    }


async def _register(client, organization: str = "") -> tuple[dict, str]:
    creds = _creds("reg")
    resp = await client.post("/api/v1/auth/register", json={**creds, "organization": organization})
    assert resp.status_code == 201, resp.text
    return creds, resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_register_login_me_roundtrip(client):
    creds, token = await _register(client)

    me = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == creds["email"]
    assert me.json()["role"] == "owner"

    login = await client.post(
        "/api/v1/auth/login", data={"username": creds["email"], "password": creds["password"]}
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad = await client.post(
        "/api/v1/auth/login", data={"username": creds["email"], "password": "wrong-password"}
    )
    assert bad.status_code == 401


async def test_free_tier_blocks_document_upload(client):
    _, token = await _register(client)
    resp = await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 402  # Free tier has no document upload


async def test_free_tier_daily_message_quota(client):
    """21st message on the Free plan must raise PlanLimitExceeded (429 at API level)."""
    from sqlalchemy import select

    from app.db.base import async_session_factory
    from app.models import User
    from app.services.billing.plans import PlanLimitExceeded, check_and_increment

    creds, _ = await _register(client)
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.email == creds["email"]))).scalar_one()
        for _ in range(20):
            await check_and_increment(db, user, "messages")
        with pytest.raises(PlanLimitExceeded):
            await check_and_increment(db, user, "messages")
        await db.rollback()


async def test_tenant_isolation_documents(client):
    """A document belonging to tenant A must be invisible to tenant B."""
    from app.db.base import async_session_factory
    from app.models import Document
    from sqlalchemy import select

    from app.models import User

    creds_a, token_a = await _register(client, organization="Org Alpha")
    _, token_b = await _register(client, organization="Org Beta")

    async with async_session_factory() as db:
        user_a = (await db.execute(select(User).where(User.email == creds_a["email"]))).scalar_one()
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            uploaded_by=user_a.id,
            title="secret-contract.pdf",
            storage_key="k",
            status="ready",
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    list_a = await client.get("/api/v1/documents", headers=_auth(token_a))
    assert any(d["id"] == str(doc_id) for d in list_a.json())

    list_b = await client.get("/api/v1/documents", headers=_auth(token_b))
    assert all(d["id"] != str(doc_id) for d in list_b.json())

    get_b = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token_b))
    assert get_b.status_code == 404


async def test_rag_eval_smoke(client):
    """Seed a few legislation chunks and verify the eval metrics pipeline."""
    from app.db.base import async_session_factory
    from app.models import DocumentChunk, Tenant
    from app.scripts.rag_eval import evaluate
    from app.services.rag.retrieval import LEGISLATION_TENANT_ID
    from sqlalchemy import select

    async with async_session_factory() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == LEGISLATION_TENANT_ID))
        ).scalar_one_or_none()
        if tenant is None:
            db.add(Tenant(id=LEGISLATION_TENANT_ID, name="Legislation (shared)", slug="legislation"))
            # flush before adding chunks: DocumentChunk has no ORM relationship
            # to Tenant, so SQLAlchemy won't order these inserts by the FK
            await db.flush()
        for num, text in [
            ("130", "130-modda. Dastlabki sinov muddati uch oydan oshmasligi kerak."),
            ("182", "182-modda. Ish vaqtining normal davomiyligi haftasiga 40 soatdan ortiq bo'lishi mumkin emas."),
        ]:
            db.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    tenant_id=LEGISLATION_TENANT_ID,
                    seq=0,
                    text=text,
                    meta={"article": num, "title": "Mehnat kodeksi"},
                )
            )
        await db.commit()

        samples = [
            {"question": "Dastlabki sinov muddati qancha?", "article": "130"},
            {"question": "Ish vaqtining normal davomiyligi qancha soat?", "article": "182"},
        ]
        report = await evaluate(db, samples, top_k=5)
    assert report.total == 2
    assert report.hit_at_k == 1.0
    assert report.mrr > 0.5


async def test_agents_gated_by_free_plan(client):
    _, token = await _register(client)
    resp = await client.get("/api/v1/agents", headers=_auth(token))
    assert resp.status_code == 200
    agents = {a["slug"]: a["available"] for a in resp.json()}
    assert agents["hr"] is True
    assert agents["legal"] is False  # Business+ only

    chat = await client.post(
        "/api/v1/chat", headers=_auth(token), json={"message": "test", "agent": "legal"}
    )
    assert chat.status_code == 402
