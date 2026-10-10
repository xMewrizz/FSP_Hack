from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator
from app.core.constants import SPECIALIZATIONS


class TaskFileResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    download_url: str


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
    specialization: str | None = None
    min_grade: str | None = None
    max_grade: str | None = None
    evaluation_criteria: list[str] = Field(default_factory=list, max_length=20)
    resource_links: list[str] = Field(default_factory=list, max_length=20)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)

    @field_validator("reference_answer")
    @classmethod
    def validate_reference_answer(cls, v: str | None, values) -> str | None:
        return v

    @model_validator(mode="after")
    def validate_scope(self):
        grades = ("junior", "middle", "senior", "lead")
        if self.specialization is not None and self.specialization not in SPECIALIZATIONS:
            raise ValueError("Выберите специализацию из каталога")
        if (self.min_grade is None) != (self.max_grade is None):
            raise ValueError("Укажите обе границы грейда или оставьте обе пустыми")
        if self.min_grade is not None:
            if self.min_grade not in grades or self.max_grade not in grades:
                raise ValueError("Выберите грейд из каталога")
            if grades.index(self.min_grade) > grades.index(self.max_grade):
                raise ValueError("Начальный грейд не может быть выше конечного")
        if any(not item.strip() for item in self.evaluation_criteria):
            raise ValueError("Критерии оценивания не должны быть пустыми")
        if any(not link.startswith(("https://", "http://")) for link in self.resource_links):
            raise ValueError("Ссылки на материалы должны начинаться с http:// или https://")
        return self


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
    specialization: str | None = None
    min_grade: str | None = None
    max_grade: str | None = None
    evaluation_criteria: list[str] = Field(default_factory=list)
    resource_links: list[str] = Field(default_factory=list)
    is_platform_task: bool = False
    attachments: list["TaskFileResponse"] = Field(default_factory=list)
    is_active: bool
    submissions_count: int = 0
    created_at: datetime
    updated_at: datetime


class EmployerTaskSubmissionCreate(BaseModel):
    answer_text: str = Field(..., min_length=1, description="Ответ или решение кандидата")
    answer_links: list[str] = Field(default_factory=list, max_length=20)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)


class EmployerTaskSubmissionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str | None = None
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    answer_text: str
    answer_links: list[str] = Field(default_factory=list)
    contact_consent: bool = False
    attachments: list["TaskFileResponse"] = Field(default_factory=list)
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
    specialization: str | None = None
    min_grade: str | None = None
    max_grade: str | None = None
    evaluation_criteria: list[str] = Field(default_factory=list)
    resource_links: list[str] = Field(default_factory=list)
    is_platform_task: bool = False
    attachments: list["TaskFileResponse"] = Field(default_factory=list)
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
