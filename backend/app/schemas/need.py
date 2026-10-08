from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.constants import Grade, WorkFormat


class SkillRequirement(BaseModel):
    name: str
    weight: float = 1.0
    required: bool = True


class EmployerNeedCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    specialization: str = Field(..., min_length=2, max_length=100)
    required_grade: Grade
    required_skills: list[SkillRequirement] = Field(default_factory=list)
    salary_min: float = Field(..., gt=0)
    salary_max: float = Field(..., gt=0)
    salary_tax_type: Literal["gross", "net"] = "gross"
    currency: str = "RUB"
    work_format: WorkFormat = WorkFormat.REMOTE
    city: str | None = None
    description: str = ""

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
    salary_tax_type: Literal["gross", "net"] | None = None
    currency: str | None = None
    work_format: WorkFormat | None = None
    city: str | None = None
    description: str | None = None
    is_active: bool | None = None

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
