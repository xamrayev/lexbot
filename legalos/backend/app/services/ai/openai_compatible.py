"""Single provider implementation for every OpenAI-compatible API.

OpenAI, DeepSeek, Gemini (OpenAI-compat endpoint), Qwen (DashScope
compatible-mode), and self-hosted Gemma/vLLM/Ollama all speak the same wire
protocol, so one implementation parameterized by base_url/api_key covers the
whole provider matrix required by the spec.
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.services.ai.base import AIProvider, ChatMessage, CompletionResult


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        default_model: str,
        embedding_model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> CompletionResult:
        payload = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage", {})
        return CompletionResult(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", payload["model"]),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[len("data: ") :]
                    if chunk.strip() == "[DONE]":
                        break
                    delta = json.loads(chunk)["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        yield content

    async def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        embedding_model = model or self.embedding_model
        if not embedding_model:
            raise ValueError(f"Provider '{self.name}' has no embedding model configured")
        payload = {"model": embedding_model, "input": texts}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/embeddings", json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
