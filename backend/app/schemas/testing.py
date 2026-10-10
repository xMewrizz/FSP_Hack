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
    skill_code: str | None = None
    assessment_id: uuid.UUID | None = None


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
    correct_count: int = 0
    total_questions: int = 0


class QuestionReview(BaseModel):
    code: str
    topic: str
    question_text: str
    selected_answers: list[str]
    correct_answers: list[str]
    is_correct: bool
    explanation: str


class TestResultResponse(BaseModel):
    session_id: uuid.UUID
    specialization: str
    target_grade: str
    score: float
    max_score: float
    percentage: float
    correct_count: int
    total_questions: int
    required_correct: int
    passed: bool | None
    grade_confirmed: bool
    verified_grade: str | None
    skill_breakdown: list[SkillScore]
    question_review: list[QuestionReview]
    feedback: str
    suggested_grade: str | None
    completed_at: datetime | None
    skill_code: str | None = None
    assessment_id: uuid.UUID | None = None


class TestSessionHistoryItem(BaseModel):
    id: uuid.UUID
    specialization: str
    target_grade: str
    percentage: float
    passed: bool | None
    grade_confirmed: bool
    status: str
    created_at: datetime
    completed_at: datetime | None
    skill_code: str | None = None
    assessment_id: uuid.UUID | None = None


class AssessmentSkillProgress(BaseModel):
    code: str
    label: str
    status: str
    percentage: float | None = None
    level_out_of_ten: float | None = None
    session_id: uuid.UUID | None = None


class AssessmentOpenQuestionProgress(BaseModel):
    code: str
    title: str
    question_type: str
    status: str
    score: float | None = None
    submission_id: uuid.UUID | None = None


class GradeAssessmentResponse(BaseModel):
    id: uuid.UUID
    specialization: str
    programming_language: str | None = None
    target_grade: str
    status: str
    skills: list[AssessmentSkillProgress]
    open_questions: list[AssessmentOpenQuestionProgress] = Field(default_factory=list)
    percentage: float | None = None
    passed: bool | None = None
    grade_confirmed: bool = False
    verified_grade: str | None = None
    suggested_grade: str | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    retake_used: bool = False
    retry_available_at: datetime | None = None
    promotion_available_at: datetime | None = None


class AdditionalSkillTestResponse(BaseModel):
    code: str
    label: str
    target_grade: str
    latest_percentage: float | None = None
    level_out_of_ten: float | None = None
    latest_session_id: uuid.UUID | None = None


class OpenQuestionResponse(BaseModel):
    code: str
    title: str
    specialization: str
    grade: str
    question_type: str
    skill: str = ""
    question_text: str
    rubric_criteria: list[str]


class OpenQuestionSubmitRequest(BaseModel):
    answer_text: str
    assessment_id: uuid.UUID | None = None


class OpenQuestionSubmissionResponse(BaseModel):
    id: uuid.UUID
    question_code: str
    question_type: str
    assessment_id: uuid.UUID | None = None
    answer_text: str
    score: float
    passed: bool
    feedback: str
    criterion_scores: dict[str, Any]
    evaluator: str
    needs_manual_review: bool
    created_at: datetime
    manual_reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None


class OpenQuestionReviewRequest(BaseModel):
    score: float
    passed: bool
    notes: str | None = None

