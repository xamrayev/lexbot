"""Application configuration.

All infrastructure endpoints and AI provider credentials are configured via
environment variables so that a deployment (cloud, on-premise, Government
Edition private cloud) never requires code changes.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEGALOS_", extra="ignore")

    app_name: str = "Enterprise LegalOS"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # PostgreSQL (+ pgvector)
    database_url: str = "postgresql+asyncpg://legalos:legalos@postgres:5432/legalos"

    # Redis — cache, rate limiting, usage counters
    redis_url: str = "redis://redis:6379/0"

    # MinIO — document object storage
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "legalos"
    minio_secret_key: str = "legalos-secret"
    minio_bucket: str = "legalos-documents"
    minio_secure: bool = False

    # RabbitMQ — async pipelines (indexing, legislative sync, notifications)
    rabbitmq_url: str = "amqp://legalos:legalos@rabbitmq:5672/"

    # AI platform (provider pattern) — see services/ai/registry.py
    default_ai_provider: str = "openai"
    default_ai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    # Any OpenAI-compatible endpoint (Gemma via Ollama/vLLM, self-hosted, etc.)
    compatible_api_key: str = ""
    compatible_base_url: str = ""
    compatible_model: str = ""

    # Embeddings
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # SSO (OIDC) — Enterprise/Government single sign-on
    oidc_discovery_url: str = ""  # e.g. https://idp.example.uz/.well-known/openid-configuration
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""  # e.g. https://legalos.example.uz/api/v1/auth/sso/callback
    sso_tenant_slug: str = "sso"  # tenant that SSO users are provisioned into
    sso_auto_provision: bool = True  # create unknown users on first SSO login
    sso_state_ttl_seconds: int = 600

    # Knowledge Graph (optional Neo4j; RAG works without it)
    neo4j_uri: str = ""  # e.g. bolt://neo4j:7687 — empty disables graph expansion
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # RAG reranker: "llm" (listwise LLM), "cross_encoder" (local
    # sentence-transformers model), or "none" (fusion order)
    rag_reranker: str = "llm"
    cross_encoder_model: str = "BAAI/bge-reranker-v2-m3"

    # Legislative monitoring: how often the worker enqueues checks of all
    # tracked acts (0 disables the scheduler; manual sync stays available)
    legislation_check_interval_hours: int = 24

    # External sources
    lex_uz_base_url: str = "https://lex.uz"
    norma_uz_base_url: str = "https://norma.uz"
    mygov_base_url: str = "https://my.gov.uz"

    # Telegram
    telegram_bot_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
