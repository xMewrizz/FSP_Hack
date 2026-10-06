from typing import Any
import uuid
from pydantic import BaseModel
from app.core.constants import Grade, WorkFormat


class MatchExplanation(BaseModel):
    grade_match: bool
    matched_skills: list[str]
    missing_skills: list[str]
    fsp_bonus: bool
    summary: str


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
    test_percentage: float | None
    match_score: float
    match_explanation: MatchExplanation


class MatchingCandidatesResponse(BaseModel):
    need_id: uuid.UUID | None
    need_title: str | None
    total: int
    candidates: list[CandidateMatchItem]
