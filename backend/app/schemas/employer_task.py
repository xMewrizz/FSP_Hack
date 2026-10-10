from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, Field, field_validator


class EmployerTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Название задания")
    description: str = Field(..., min_length=1, description="Формулировка и условие задания")
    task_type: Literal["auto_check", "manual_review"] = Field(
        "manual_review",
        description="Тип проверки: auto_check (по эталону) или manual_review (оценивает работодатель)",
    )
    reference_answer: str | None = Field(
        None,
        description="Эталонный ответ для автоматической проверки (обязателен, если task_type='auto_check')",
    )
    max_score: float = Field(10.0, gt=0, description="Максимальный балл за задание")
    vacancy_id: uuid.UUID | None = Field(None, description="Привязка к вакансии (опционально)")

    @field_validator("reference_answer")
    @classmethod
    def validate_reference_answer(cls, v: str | None, values) -> str | None:
        return v


class EmployerTaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    reference_answer: str | None = None
    max_score: float | None = Field(None, gt=0)
    is_active: bool | None = None


class EmployerTaskResponse(BaseModel):
    id: uuid.UUID
    employer_id: uuid.UUID
    vacancy_id: uuid.UUID | None = None
    company_name: str | None = None
    title: str
    description: str
    task_type: str
    reference_answer: str | None = None
    max_score: float
    is_active: bool
    submissions_count: int = 0
    created_at: datetime
    updated_at: datetime


class EmployerTaskSubmissionCreate(BaseModel):
    answer_text: str = Field(..., min_length=1, description="Ответ или решение кандидата")


class EmployerTaskSubmissionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str | None = None
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    answer_text: str
    status: str
    score: float | None = None
    max_score: float
    passed: bool | None = None
    feedback: str | None = None
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class CandidateTaskResponse(BaseModel):
    id: uuid.UUID
    employer_id: uuid.UUID
    vacancy_id: uuid.UUID | None = None
    company_name: str
    title: str
    description: str
    task_type: str
    max_score: float
    created_at: datetime
    my_submission: EmployerTaskSubmissionResponse | None = None


class EmployerTaskReviewRequest(BaseModel):
    score: float = Field(..., ge=0.0, description="Выставленный балл")
    passed: bool = Field(..., description="Пройдено ли задание")
    feedback: str | None = Field(None, description="Комментарий к оценке")


class CandidateActivityResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    activity_type: str
    title: str
    description: str | None = None
    reference_id: uuid.UUID | None = None
    created_at: datetime
