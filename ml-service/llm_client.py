"""Единый вызов JSON-ответов через локальную Ollama или OpenRouter."""

import os
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
) -> str:
    """Вернуть строку JSON; проверка содержимого остаётся за вызывающим кодом."""
    if provider_name() == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Для OpenRouter нужен OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.getenv("OPENROUTER_MODEL", "qwen/qwen3-14b"),
                "messages": messages,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "strict": True, "schema": _strict_schema(schema)},
                },
                "provider": {"require_parameters": True},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
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
