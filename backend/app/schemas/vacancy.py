from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, Field, field_validator


class VacancyBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Название вакансии")
    specialization: str = Field(..., max_length=100, description="Специализация (например Backend, Frontend)")
    required_grade: str = Field(..., max_length=50, description="Грейд (Junior, Middle, Senior, Lead)")
    required_skills: list[str] = Field(default_factory=list, description="Список ключевых навыков")
    salary_min: float = Field(..., ge=0, description="Зарплата от (в рублях)")
    salary_max: float = Field(..., ge=0, description="Зарплата до (в рублях)")
    salary_tax_type: Literal["gross", "net"] = Field(
        "gross",
        description="Пометка: 'gross' (до вычета НДФЛ) или 'net' (на руки)",
    )
    currency: str = Field("RUB", max_length=10, description="Валюта (RUB)")
    work_format: str = Field("remote", max_length=50, description="Формат: remote, office, hybrid")
    city: str | None = Field(None, max_length=100, description="Город (для гибрида/офиса)")
    description: str = Field("", description="Описание вакансии и команды")


class VacancyCreate(VacancyBase):
    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, v: float, info) -> float:
        salary_min = info.data.get("salary_min")
        if salary_min is not None and v < salary_min:
            raise ValueError("salary_max не может быть меньше salary_min")
        return v


class VacancyUpdate(BaseModel):
    title: str | None = None
    specialization: str | None = None
    required_grade: str | None = None
    required_skills: list[str] | None = None
    salary_min: float | None = Field(None, ge=0)
    salary_max: float | None = Field(None, ge=0)
    salary_tax_type: Literal["gross", "net"] | None = None
    currency: str | None = None
    work_format: str | None = None
    city: str | None = None
    description: str | None = None
    is_published: bool | None = None


class CompanyShortInfo(BaseModel):
    id: uuid.UUID
    company_name: str
    industry: str | None = None
    website: str | None = None
    city: str | None = None


class VacancyResponse(VacancyBase):
    id: uuid.UUID
    employer_id: uuid.UUID
    is_published: bool
    created_at: datetime
    updated_at: datetime
    company: CompanyShortInfo | None = None


class ApplicationCreate(BaseModel):
    cover_letter: str | None = Field(None, max_length=2000, description="Сопроводительное письмо")


class ApplicationCandidateResponse(BaseModel):
    id: uuid.UUID
    vacancy_id: uuid.UUID
    status: str
    cover_letter: str | None
    created_at: datetime
    status_updated_at: datetime | None = None
    vacancy_title: str
    company_name: str
    salary_min: float
    salary_max: float
    salary_tax_type: str


class CandidateContactInfo(BaseModel):
    candidate_id: uuid.UUID
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: str
    phone: str | None = None
    telegram: str | None = None
    city: str | None = None
    github_url: str | None = None
    specialization: str | None = None
    declared_grade: str | None = None
    verified_grade: str | None = None
    skills: list[str] = Field(default_factory=list)
    resume_text: str | None = None


class ApplicationEmployerResponse(BaseModel):
    id: uuid.UUID
    vacancy_id: uuid.UUID
    status: str
    cover_letter: str | None
    created_at: datetime
    status_updated_at: datetime | None = None
    candidate: CandidateContactInfo


class ApplicationStatusUpdate(BaseModel):
    status: Literal["pending", "reviewed", "accepted", "rejected"]
