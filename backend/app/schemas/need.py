from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core.constants import Grade, WorkFormat


class SkillRequirement(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(default=1.0, ge=0.1, le=10.0, description="Важность навыка (рекомендуется шкала 1..5)")
    required: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Название навыка не может быть пустым")
        return clean


class NeedTextRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=5000)


class NeedDraftResponse(BaseModel):
    source: Literal["llm"]
    specialization: str | None = None
    required_grade: Grade | None = None
    required_skills: list[SkillRequirement] = Field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_tax_type: Literal["gross", "net"] | None = None
    work_format: WorkFormat | None = None


class EmployerNeedCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    specialization: str = Field(..., min_length=2, max_length=100)
    required_grade: Grade
    required_skills: list[SkillRequirement] = Field(default_factory=list)
    salary_min: float = Field(..., gt=0)
    salary_max: float = Field(..., gt=0)
    salary_tax_type: Literal["gross", "net"] = Field(
        "gross",
        description="Тип зарплаты: «до вычета НДФЛ» (gross) или «на руки» (net)",
    )
    currency: str = "RUB"
    work_format: WorkFormat = WorkFormat.REMOTE
    city: str | None = None
    description: str = ""

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

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min > self.salary_max:
            raise ValueError("salary_min не может быть больше salary_max")
        return self


class EmployerNeedUpdate(BaseModel):
    title: str | None = None
    specialization: str | None = None
    required_grade: Grade | None = None
    required_skills: list[SkillRequirement] | None = None
    salary_min: float | None = Field(default=None, gt=0)
    salary_max: float | None = Field(default=None, gt=0)
    salary_tax_type: Literal["gross", "net"] | None = Field(
        default=None,
        description="Тип зарплаты: «до вычета НДФЛ» (gross) или «на руки» (net)",
    )
    currency: str | None = None
    work_format: WorkFormat | None = None
    city: str | None = None
    description: str | None = None
    is_active: bool | None = None

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

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min не может быть больше salary_max")
        return self


class EmployerNeedResponse(BaseModel):
    id: uuid.UUID
    employer_id: uuid.UUID
    company_name: str
    title: str
    specialization: str
    required_grade: str
    required_skills: list[SkillRequirement]
    salary_min: float
    salary_max: float
    salary_tax_type: str = "gross"
    currency: str
    work_format: str
    city: str | None
    description: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
