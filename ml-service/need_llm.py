"""Предложение навыков и их важности по описанию потребности."""

from __future__ import annotations

import os
import re
from typing import TypedDict

import httpx
from pydantic import BaseModel, Field, ValidationError

from need_parser import SKILLS, SPECIALIZATIONS, parse_need, skill_mentions
from llm_client import chat_json


class SkillDraft(TypedDict):
    name: str
    weight: int


MAX_SKILLS = 10
TECH_SKILLS = {name for name, _ in SKILLS}
GENERIC_SKILLS = {
    "HTTP API": r"\bapi\b|апи|webhook|вебхук|интеграц",
    "Надёжность сервиса": r"нагруз|отказ|сбо|тайм[ -]?аут|над[её]жност",
    "Проектирование БД": r"хран|баз[а-я ]*данн|витрин|схем[а-я ]*данн",
    "Авторизация": r"авторизац|аутентификац|прав[а-я ]*доступ",
    "Нагрузочное тестирование": r"нагруз",
    "Производительность": r"производител|нагруз|оптимизац",
    "Доступность интерфейсов": r"доступност",
    "Автотестирование": r"автотест|автоматизац[а-я ]*тест",
    "Тестирование API": r"(?=.*(?:тест|провер))(?=.*(?:\bapi\b|апи))",
    "Тестирование веб-приложений": r"(?=.*(?:тест|провер))(?=.*(?:веб[ -]?прилож|интерфейс))",
    "Анализ ошибок": r"ошиб|отлад",
    "Мониторинг": r"монитор|следить за (?:логами и )?метрик|наблюда",
    "Логирование": r"\bлог(?:и|ов|ами)?\b|\bлогир\w*|\bжурнал\w*",
    "Анализ данных": r"анализ[а-я ]*данн|анализ\w*\s+поведен|исслед|витрин",
    "Продуктовые метрики": r"продуктов[а-я ]*метрик|поведен\w*\s+пользоват|предлаг\w*.*услуг",
    "Машинное обучение": r"модел|классификац|\bml\b|машинн[а-я ]*обуч",
    "Подготовка данных": r"подготов[а-я ]*данн|предобработ|витрин|поведен\w*\s+пользоват",
    "Оценка моделей": r"качеств[а-я ]*модел|отложенн[а-я ]*выбор|валидац[а-я ]*модел|\bml[ -]?модел|машинн[а-я ]*обуч",
    "Развёртывание моделей": r"внедр\w*.*модел|разв[её]рт[а-я ]*модел|модел[а-я ]*сервис",
    "Рекомендательные системы": r"рекоменд\w*|предлаг\w*.*услуг",
    "Офлайн-хранение": r"офлайн|offline|локальн[а-я ]*хран",
    "Публикация приложений": r"публикац[а-я ]*прилож|публикац[а-я ]*обновлен",
}
KNOWN_SKILLS = {name.casefold(): name for name in TECH_SKILLS | GENERIC_SKILLS.keys()}
ALIASES = {
    "rest api": "HTTP API",
    "restful services": "HTTP API",
    "api design": "HTTP API",
    "проектирование http api": "HTTP API",
    "работа с api": "HTTP API",
    "разработка api": "HTTP API",
    "database design": "Проектирование БД",
    "authentication & authorization": "Авторизация",
    "load testing": "Нагрузочное тестирование",
    "performance optimization": "Производительность",
    "accessibility (a11y)": "Доступность интерфейсов",
    "аccessibility (a11y)": "Доступность интерфейсов",
    "unit testing": "Автотестирование",
    "monitoring": "Мониторинг",
    "log management": "Логирование",
    "data preparation": "Подготовка данных",
    "model evaluation": "Оценка моделей",
    "model deployment": "Развёртывание моделей",
    "machine learning": "Машинное обучение",
    "apache spark": "Spark",
    "a/b-тестирование": "A/B-тесты",
    "a/b testing": "A/B-тесты",
}


def _canonical_skill(name: str, text: str) -> str | None:
    clean = " ".join(name.split())
    key = clean.casefold()
    if key in ALIASES:
        return ALIASES[key]
    if key in KNOWN_SKILLS:
        return KNOWN_SKILLS[key]
    # Новую технологию можно предложить, только когда её написал работодатель.
    return clean if len(clean) >= 2 and key in text.casefold() else None


def _checked_skills(text: str, suggestions: list[SuggestedSkill]) -> list[SkillDraft]:
    mentions = skill_mentions(text)
    result: dict[str, SkillDraft] = {}
    for item in suggestions:
        name = _canonical_skill(item.name, text)
        if not name or mentions.get(name) == "excluded":
            continue
        if name in TECH_SKILLS and name not in mentions:
            continue
        if name in GENERIC_SKILLS and not re.search(GENERIC_SKILLS[name], text, re.IGNORECASE):
            continue
        weight = min(item.weight, 2) if mentions.get(name) == "optional" else item.weight
        if mentions.get(name) == "core":
            weight = max(weight, 4)
        key = name.casefold()
        if key not in result:
            result[key] = {"name": name, "weight": weight}
        else:
            result[key]["weight"] = max(result[key]["weight"], weight)

    # Явно названные технологии не должны пропадать из ответа модели.
    for name, importance in mentions.items():
        if importance == "excluded":
            continue
        key = name.casefold()
        weight = 2 if importance == "optional" else 4
        if key not in result:
            result[key] = {"name": name, "weight": weight}
    return list(result.values())[:MAX_SKILLS]


class SuggestedSkill(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    weight: int = Field(ge=1, le=5)


class SuggestedNeed(BaseModel):
    specialization: str | None = None
    skills: list[SuggestedSkill] = Field(max_length=10)


SYSTEM_PROMPT = """Ты помогаешь работодателю составить фильтр поиска ИТ-кандидата.
По описанию задач предложи до 8 технических навыков и их важность от 1 до 5.
5 — без этого навыка роль трудно выполнить; 4 — важный; 3 — полезный;
1–2 — дополнительный. «Будет плюсом» и «желательно» означают вес не выше 2.
«Не нужен», «знать необязательно» или «без» — не включай навык.
Названные технологии не пропускай. Не придумывай конкретные
фреймворки, базы данных, облака и инструменты, которых нет в описании.
Если технологии не названы, предлагай только навыки, прямо связанные с задачами.
Если система предлагает пользователям товары или услуги по их поведению,
рассмотри навык «Рекомендательные системы».
Используй по возможности такие названия: {skills}. Новую технологию вне списка
можно добавить, только когда она прямо названа работодателем.
Не добавляй общие качества вроде «коммуникабельность» и не повторяй навык.
Специализацию выбери только если направление понятно из текста. Допустимы:
{specializations}. Если непонятно, верни null. Не придумывай зарплату и грейд:
их система определяет отдельно только по явному указанию в тексте.
Верни только JSON по заданной схеме."""


async def suggest_need(text: str, client: httpx.AsyncClient) -> dict:
    host = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    schema = SuggestedNeed.model_json_schema()
    raw_content = await chat_json(
        client,
        messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(
                    specializations=", ".join(name for name, _ in SPECIALIZATIONS),
                    skills=", ".join(sorted(TECH_SKILLS | GENERIC_SKILLS.keys())),
                )},
                {"role": "user", "content": text},
        ],
        schema=schema,
        schema_name="suggested_need",
        ollama_url=host,
        ollama_model=model,
    )
    try:
        suggested = SuggestedNeed.model_validate_json(raw_content)
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise ValueError("Модель вернула некорректный список навыков") from exc

    skills = _checked_skills(text, suggested.skills)
    if not skills:
        raise ValueError("Не удалось подобрать навыки по описанию")

    explicit = parse_need(text)
    known_specializations = {name for name, _ in SPECIALIZATIONS}
    specialization = explicit["specialization"] or (
        suggested.specialization if suggested.specialization in known_specializations else None
    )
    return {
        **explicit,
        "specialization": specialization,
        "required_skills": skills,
        "source": "llm",
    }
