from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, Field, field_validator
from app.core.constants import Grade, WorkFormat
from app.schemas.fsp import FSPAchievementSchema


class CandidateOnboardingRequest(BaseModel):
    # 152-ФЗ
    agreed_152_fz: bool = Field(False, description="Согласие на обработку персональных данных (152-ФЗ)")
    agreed_publication: bool = Field(False, description="Отдельное согласие показывать профиль работодателям")
    visibility_public: bool = Field(False, description="Показывать профиль в поиске и подборке")
    # Согласие на OSINT
    agreed_osint: bool = Field(False, description="Согласие на обогащение профиля открытыми данными (OSINT)")
    
    # IT-специализация и грейд
    specialization: str = Field(..., description="IT-специализация (Backend, Frontend, etc.)")
    programming_language: str | None = Field(None, description="Язык программирования для базового теста")
    declared_grade: Grade = Field(..., description="Предполагаемый грейд (junior, middle, senior, lead)")
    
    # Формат работы и город
    work_format: WorkFormat = Field(WorkFormat.REMOTE, description="Формат работы (remote, office, hybrid)")
    city: str = Field(..., description="Город проживания/работы")

    # Зарплатные ожидания и навыки
    salary_expectation: float | None = Field(None, gt=0, description="Ожидания по зарплате (в рублях)")
    salary_tax_type: Literal["gross", "net"] = Field("gross", description="«до вычета НДФЛ» (gross) или «на руки» (net)")
    skills: list[str] = Field(default_factory=list, description="Навыки соискателя")

    @field_validator("salary_tax_type", mode="before")
    @classmethod
    def normalize_tax_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("gross", "до вычета", "до вычета ндфл", "до вычета ндфл (gross)"):
                return "gross"
            if clean in ("net", "на руки", "на руки (net)"):
                return "net"
        return v

    # ФСП ID (опционально)
    fsp_id: str | None = Field(None, description="ID участника ФСП (если есть)")

    # Личные данные
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    telegram: str | None = Field(None, max_length=100)
    bio: str | None = None
    github_url: str | None = None


class CandidateProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    phone: str | None = None
    telegram: str | None = None
    bio: str | None = None
    city: str | None = None
    github_url: str | None = None
    work_format: WorkFormat | None = None
    specialization: str | None = None
    programming_language: str | None = None
    declared_grade: Grade | None = None
    salary_expectation: float | None = Field(default=None, gt=0)
    salary_tax_type: Literal["gross", "net"] | None = None
    skills: list[str] | None = None
    fsp_id: str | None = None
    agreed_publication: bool | None = None
    visibility_public: bool | None = None

    @field_validator("salary_tax_type", mode="before")
    @classmethod
    def normalize_tax_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("gross", "до вычета", "до вычета ндфл", "до вычета ндфл (gross)"):
                return "gross"
            if clean in ("net", "на руки", "на руки (net)"):
                return "net"
        return v


class CandidateProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str | None = None
    telegram: str | None = None
    bio: str | None = None
    city: str | None = None
    github_url: str | None = None
    resume_url: str | None = None

    specialization: str | None = None
    programming_language: str | None = None
    declared_grade: str | None = None
    verified_grade: str | None = None
    verified_specialization: str | None = None
    work_format: str | None = None
    salary_expectation: float | None = None
    salary_tax_type: str = "gross"
    skills: list[str] = []

    fsp_id: str | None = None
    fsp_verified: bool = False
    agreed_152_fz: bool
    agreed_publication: bool
    visibility_public: bool
    agreed_osint: bool
    onboarding_completed: bool

    achievements: list[FSPAchievementSchema] = []

    model_config = {"from_attributes": True}
