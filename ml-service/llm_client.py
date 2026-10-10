"""Единый вызов JSON-ответов через локальную Ollama или OpenRouter."""

import os
import time
from copy import deepcopy

import httpx


def provider_name() -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in {"ollama", "openrouter"}:
        raise ValueError("LLM_PROVIDER должен быть ollama или openrouter")
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
    if provider_name() == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Для OpenRouter нужен OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        request_body = {
            "model": os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": _strict_schema(schema)},
            },
            "provider": {"require_parameters": True},
        }
        if reasoning_enabled is not None:
            request_body["reasoning"] = {"enabled": reasoning_enabled}
        started = time.perf_counter()
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request_body,
            )
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
