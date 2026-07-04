"""Provider registry — the single place where AI vendors are wired up.

Adding a new model: add credentials to Settings, register it here. Nothing in
agents/RAG/business logic changes (spec requirement).
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.ai.base import AIProvider
from app.services.ai.openai_compatible import OpenAICompatibleProvider


@lru_cache
def _build_registry() -> dict[str, AIProvider]:
    s = get_settings()
    registry: dict[str, AIProvider] = {
        "openai": OpenAICompatibleProvider(
            "openai", s.openai_base_url, s.openai_api_key, s.default_ai_model, s.embedding_model
        ),
        "deepseek": OpenAICompatibleProvider("deepseek", s.deepseek_base_url, s.deepseek_api_key, "deepseek-chat"),
        "gemini": OpenAICompatibleProvider("gemini", s.gemini_base_url, s.gemini_api_key, "gemini-2.0-flash"),
        "qwen": OpenAICompatibleProvider("qwen", s.qwen_base_url, s.qwen_api_key, "qwen-plus"),
    }
    if s.compatible_base_url:
        # Any OpenAI-compatible endpoint: Gemma via Ollama/vLLM, on-prem models
        # for Government Edition, etc.
        registry["compatible"] = OpenAICompatibleProvider(
            "compatible", s.compatible_base_url, s.compatible_api_key, s.compatible_model or "default"
        )
    return registry


def get_provider(name: str | None = None) -> AIProvider:
    settings = get_settings()
    registry = _build_registry()
    key = name or settings.default_ai_provider
    if key not in registry:
        raise KeyError(f"Unknown AI provider '{key}'. Available: {sorted(registry)}")
    return registry[key]


def get_embedding_provider() -> AIProvider:
    return get_provider(get_settings().embedding_provider)


def list_providers() -> list[str]:
    return sorted(_build_registry())
