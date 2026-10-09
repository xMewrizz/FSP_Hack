from datetime import datetime
import uuid
from pydantic import BaseModel, Field
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
    declared_grade: Grade = Field(..., description="Предполагаемый грейд (junior, middle, senior, lead)")
    
    # Формат работы и город
    work_format: WorkFormat = Field(WorkFormat.REMOTE, description="Формат работы (remote, office, hybrid)")
    city: str = Field(..., description="Город проживания/работы")

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
    skills: list[str] | None = Field(None, description="Ключевые навыки и стек технологий")


class CandidateProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    phone: str | None = None
    telegram: str | None = None
    bio: str | None = None
    city: str | None = None
    github_url: str | None = None
    skills: list[str] | None = None
    work_format: WorkFormat | None = None
    specialization: str | None = None
    declared_grade: Grade | None = None
    fsp_id: str | None = None
    agreed_publication: bool | None = None
    visibility_public: bool | None = None


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
    declared_grade: str | None = None
    verified_grade: str | None = None
    work_format: str | None = None

    fsp_id: str | None = None
    fsp_verified: bool = False
    agreed_152_fz: bool
    agreed_publication: bool
    visibility_public: bool
    agreed_osint: bool
    onboarding_completed: bool

    achievements: list[FSPAchievementSchema] = []

    model_config = {"from_attributes": True}
