"""Единый вызов JSON-ответов через Ollama и облачные API."""

import os
import time
import asyncio
from copy import deepcopy

import httpx


def provider_name() -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in {"ollama", "openrouter", "listapi"}:
        raise ValueError("LLM_PROVIDER должен быть ollama, openrouter или listapi")
    return provider


def _strict_schema(schema: dict) -> dict:
    """Привести Pydantic-схему к обязательным полям JSON Schema API."""
    result = deepcopy(schema)

    def visit(node: object) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(result)
    return result


async def chat_json(
    client: httpx.AsyncClient,
    messages: list[dict[str, str]],
    schema: dict,
    schema_name: str,
    ollama_url: str,
    ollama_model: str,
    reasoning_enabled: bool | None = None,
    metrics: dict | None = None,
) -> str:
    """Вернуть строку JSON; проверка содержимого остаётся за вызывающим кодом."""
    provider = provider_name()
    if provider in {"openrouter", "listapi"}:
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if not api_key:
                raise ValueError("Для OpenRouter нужен OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
            model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
        else:
            api_key = os.getenv("LIST_API_KEY", "").strip()
            if not api_key:
                raise ValueError("Для List API нужен LIST_API_KEY")
            base_url = os.getenv("LIST_API_BASE_URL", "https://list-api.listapi.workers.dev/v1").rstrip("/")
            model = os.getenv("LIST_API_MODEL", "gpt-5.6-sol")
        request_body = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": _strict_schema(schema)},
            },
        }
        if provider == "openrouter":
            request_body["temperature"] = 0
            request_body["provider"] = {"require_parameters": True}
            if reasoning_enabled is not None:
                request_body["reasoning"] = {"enabled": reasoning_enabled}
        started = time.perf_counter()
        try:
            for attempt in range(2 if provider == "listapi" else 1):
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=request_body,
                )
                if provider != "listapi" or response.status_code not in {502, 503, 504} or attempt:
                    break
                await asyncio.sleep(1)
        finally:
            if metrics is not None:
                metrics["request_ms"] = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        body = response.json()
        if metrics is not None:
            usage = body.get("usage") or {}
            metrics.update({
                "generation_id": body.get("id"),
                "model": body.get("model"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            })
        content = body["choices"][0]["message"]["content"]
    else:
        response = await client.post(
            f"{ollama_url.rstrip('/')}/api/chat",
            json={
                "model": ollama_model,
                "messages": messages,
                "format": schema,
                "stream": False,
                "think": False,
                "options": {"temperature": 0, "num_ctx": 4096},
            },
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Модель вернула пустой ответ")
    return content.strip()
