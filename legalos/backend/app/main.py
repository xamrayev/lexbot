"""Enterprise LegalOS API entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agents, auth, chat, compliance, documents, gov, legislation, search, sso
from app.core.config import get_settings
from app.db.base import Base, engine
from app.services.ai.registry import list_providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables + pgvector extension on startup.
    # Production deployments manage schema with Alembic migrations instead.
    settings = get_settings()
    if settings.environment == "development":
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="AI ecosystem for legal, HR, accounting and management automation (Republic of Uzbekistan)",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def auth_rate_limit(request, call_next):
        # Per-IP brute-force protection on authentication endpoints.
        if request.method == "POST" and "/auth/" in request.url.path:
            from fastapi.responses import JSONResponse

            from app.services.billing.limiter import hit_ip_limit

            ip = request.client.host if request.client else ""
            if await hit_ip_limit(ip):
                return JSONResponse(
                    {"detail": "Too many authentication attempts, try again later"}, status_code=429
                )
        return await call_next(request)

    prefix = settings.api_v1_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(sso.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(legislation.router, prefix=prefix)
    app.include_router(gov.router, prefix=prefix)
    app.include_router(compliance.router, prefix=prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.app_name, "providers": list_providers()}

    return app


app = create_app()
