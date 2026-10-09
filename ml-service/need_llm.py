"""Предложение навыков и их важности по описанию потребности через Ollama."""

import os

import httpx
from pydantic import BaseModel, Field, ValidationError

from need_parser import SPECIALIZATIONS, parse_need


class SuggestedSkill(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    weight: int = Field(ge=1, le=5)


class SuggestedNeed(BaseModel):
    specialization: str | None = None
    skills: list[SuggestedSkill] = Field(max_length=10)


SYSTEM_PROMPT = """Ты помогаешь работодателю составить фильтр поиска ИТ-кандидата.
По описанию задач предложи до 8 технических навыков и их важность от 1 до 5.
5 — без этого навыка роль трудно выполнить; 4 — важный; 3 — полезный;
1–2 — дополнительный. Навыки можно предложить и тогда, когда работодатель
описал задачи, но не назвал технологии. Не добавляй общие качества вроде
«коммуникабельность». Не повторяй один навык под разными именами.
Специализацию выбери только если направление понятно из текста. Допустимы:
{specializations}. Если непонятно, верни null. Не придумывай зарплату и грейд:
их система определяет отдельно только по явному указанию в тексте.
Верни только JSON по заданной схеме."""


async def suggest_need(text: str, client: httpx.AsyncClient) -> dict:
    host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    schema = SuggestedNeed.model_json_schema()
    response = await client.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.format(specializations=", ".join(name for name, _ in SPECIALIZATIONS))},
                {"role": "user", "content": text},
            ],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        },
    )
    response.raise_for_status()
    try:
        suggested = SuggestedNeed.model_validate_json(response.json()["message"]["content"])
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise ValueError("Модель вернула некорректный список навыков") from exc

    if not suggested.skills:
        raise ValueError("Модель не предложила навыки")
    names = [skill.name.strip().casefold() for skill in suggested.skills]
    if any(not name for name in names):
        raise ValueError("Модель вернула пустое название навыка")
    if len(names) != len(set(names)):
        raise ValueError("Модель повторила навык")

    explicit = parse_need(text)
    known_specializations = {name for name, _ in SPECIALIZATIONS}
    specialization = explicit["specialization"] or (
        suggested.specialization if suggested.specialization in known_specializations else None
    )
    return {
        **explicit,
        "specialization": specialization,
        "required_skills": [
            {"name": skill.name.strip(), "weight": skill.weight}
            for skill in suggested.skills
        ],
        "source": "llm",
    }
