from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class ExperienceAuditStatus(str, Enum):
    NORMAL = "расхождений не найдено"
    POSSIBLY_INFLATED = "возможно крутит опыт"
    INSUFFICIENT_DATA = "недостаточно данных"


class ExternalWorkPeriod(BaseModel):
    company: str
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_months: int = 0
    is_current: bool = False
    description: str | None = None


class ParsedExternalProfile(BaseModel):
    source: Literal["habr_career", "careerist", "profi_ru"]
    source_name: str
    url: str | None = None
    identifier: str | None = None
    full_name: str | None = None
    headline: str | None = None
    location: str | None = None
    total_experience_months: int = 0
    work_periods: list[ExternalWorkPeriod] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    rating: float | None = None
    orders_count: int | None = None
    is_freelance_or_part_time: bool = False
    terms_and_access_note: str | None = None
    api_status: str | None = None


class HabrCareerApiCheck(BaseModel):
    rules_url: str = "https://career.habr.com/info/legal/api_rules"
    app_registered: bool = False
    habr_activated: bool = False
    can_access_api: bool = False
    full_search_limited: bool = True
    returned_fields: list[str] = Field(
        default_factory=lambda: [
            "first_name",
            "last_name",
            "title",
            "companies",
            "experience_dates",
            "duration",
            "skills",
            "qualifications",
        ]
    )
    legal_summary: str = (
        "Использование API требует обязательной регистрации приложения и активации администрацией Хабра. "
        "Полнотекстовый поиск по базе кандидатов ограничен; API возвращает профиль со структурированной "
        "историей работы, должностями, сроками и подтверждёнными навыками."
    )


class CareeristAccessCheck(BaseModel):
    catalog_url: str = "https://careerist.ru/cvs-programmist/"
    terms_of_use_verified: bool = True
    captcha_bypass_attempted: bool = False
    full_cv_access: bool = False
    access_level: Literal["preview_snippets", "authorized_employer_full"] = "preview_snippets"
    legal_summary: str = (
        "Отсутствие капчи не означает отсутствия ограничений и условий использования. "
        "Открытый каталог резюме программистов отдаёт сниппеты опыта и стажа; "
        "доступ к полным резюме требует авторизации работодателя и соблюдения условий сервиса."
    )


class ProfiRuActivityCheck(BaseModel):
    catalog_url: str = "https://profi.ru/it_freelance/data-scientist/"
    is_freelance_or_tutoring: bool = True
    does_not_indicate_inflated_experience: bool = True
    legal_summary: str = (
        "Профили на Профи.ру отражают частную практику, репетиторство и фриланс-заказы. "
        "Само наличие подработки на Профи.ру не означает завышения опыта и не является нарушением."
    )


class ExperienceVerificationAudit(BaseModel):
    candidate_id: uuid.UUID | None = None
    status: ExperienceAuditStatus
    is_flagged_for_inflation: bool = False
    claimed_experience_months: int = 0
    verified_formal_experience_months: int = 0
    freelance_experience_months: int = 0
    discrepancy_months: int = 0
    discrepancy_ratio: float = 1.0
    flags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    external_profiles: list[ParsedExternalProfile] = Field(default_factory=list)
    habr_check: HabrCareerApiCheck | None = None
    careerist_check: CareeristAccessCheck | None = None
    profi_check: ProfiRuActivityCheck | None = None
    audit_summary: str = ""
    employer_guidance: str = ""
    # Explicit privacy guard: False for candidate views
    visible_to_candidate: bool = False


class CandidateSanitizedAuditView(BaseModel):
    candidate_id: uuid.UUID
    has_external_data: bool = False
    sources_connected: list[str] = Field(default_factory=list)
    summary: str = "Профиль сопоставлен с открытыми источниками."
