from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field
from app.core.constants import Grade, WorkFormat


class MatchExplanation(BaseModel):
    grade_match: bool
    matched_skills: list[str]
    missing_skills: list[str]
    fsp_bonus: bool
    salary_match: bool | None = None
    salary_note: str | None = None
    summary: str


class RequestedSkillTestResult(BaseModel):
    name: str
    weight: float
    percentage: float | None = None
    test_grade: str | None = None
    test_kind: str | None = None
    completed_at: datetime | None = None


class CandidateMatchItem(BaseModel):
    candidate_id: uuid.UUID
    first_name: str
    last_name: str
    specialization: str | None
    verified_grade: str | None
    declared_grade: str | None
    city: str | None
    work_format: str | None
    fsp_id: str | None
    fsp_verified: bool
    fsp_sport_category: str | None
    fsp_rating: float | None
    achievements_count: int
    skills: list[str]
    salary_expectation: float | None = None
    salary_tax_type: str | None = None
    test_percentage: float | None
    match_score: float
    match_explanation: MatchExplanation
    requested_skill_tests: list[RequestedSkillTestResult] = Field(default_factory=list)


class MatchingCandidatesResponse(BaseModel):
    need_id: uuid.UUID | None
    need_title: str | None
    total: int
    candidates: list[CandidateMatchItem]
