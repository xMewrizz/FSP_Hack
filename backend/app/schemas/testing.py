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
    created_at: datetime
    completed_at: datetime | None
