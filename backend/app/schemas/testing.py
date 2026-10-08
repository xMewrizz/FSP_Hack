from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field
from app.core.constants import Grade


class TestStartRequest(BaseModel):
    specialization: str | None = None
    target_grade: Grade | None = None


class QuestionOptionResponse(BaseModel):
    id: str
    text: str


class QuestionInTest(BaseModel):
    id: str
    code: str
    topic: str
    question_type: str
    question_text: str
    options: list[QuestionOptionResponse]
    weight: float = 1.0


class TestStartResponse(BaseModel):
    session_id: uuid.UUID
    specialization: str
    target_grade: str
    status: str
    questions: list[QuestionInTest]
    total_questions: int


class AnswerSubmission(BaseModel):
    question_id: str
    selected_answers: list[str]


class TestSubmitRequest(BaseModel):
    answers: list[AnswerSubmission]


class SkillScore(BaseModel):
    topic: str
    score: float
    max_score: float
    percentage: float


class TestResultResponse(BaseModel):
    session_id: uuid.UUID
    specialization: str
    target_grade: str
    score: float
    max_score: float
    percentage: float
    passed: bool
    verified_grade: str | None
    skill_breakdown: list[SkillScore]
    feedback: str
    suggested_grade: str | None
    completed_at: datetime | None


class TestSessionHistoryItem(BaseModel):
    id: uuid.UUID
    specialization: str
    target_grade: str
    percentage: float
    passed: bool
    status: str
    suggested_grade: str | None = None
    created_at: datetime
    completed_at: datetime | None


class AvailableGradeInfo(BaseModel):
    grade: str
    is_available: bool
    is_recommended: bool
    is_current_verified: bool
    reason: str | None = None


class TestingStatusResponse(BaseModel):
    specialization: str | None = None
    declared_grade: str | None = None
    verified_grade: str | None = None
    verified_grade_updated_at: datetime | None = None
    cooldown_active: bool = False
    cooldown_days_remaining: int = 0
    cooldown_expires_at: datetime | None = None
    last_completed_test: TestSessionHistoryItem | None = None
    suggested_grade: str | None = None
    recommended_action: str
    available_grades: list[AvailableGradeInfo]

