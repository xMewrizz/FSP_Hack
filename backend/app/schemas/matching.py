from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field
from app.core.constants import Grade, WorkFormat
from app.schemas.profile_completeness import PublicProfileCompleteness


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


class CandidateAdditionalSpecialization(BaseModel):
    specialization: str
    declared_grade: str | None = None
    status: str
    verified_grade: str | None = None


class TrustFlagItem(BaseModel):
    label: str
    status: str
    detail: str


class CandidateMatchItem(BaseModel):
    candidate_id: uuid.UUID
    profile_completeness: PublicProfileCompleteness
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
    bio: str | None = None
    hobbies: str | None = None
    education_level: str | None = None
    university_course: int | None = None
    birth_year: int | None = None
    photo_url: str | None = None
    github_url: str | None = None
    resume_text: str | None = None
    resume_employers: list[str] = Field(default_factory=list)
    resume_url: str | None = None
    salary_expectation: float | None = None
    salary_tax_type: str | None = None
    test_percentage: float | None
    activity_status: str = "Не активен"
    match_score: float
    match_explanation: MatchExplanation
    requested_skill_tests: list[RequestedSkillTestResult] = Field(default_factory=list)
    additional_specializations: list[CandidateAdditionalSpecialization] = Field(default_factory=list)
    trust_score: float | None = None
    trust_flags: list[TrustFlagItem] | None = None
    profile_updated_at: datetime | None = None


class MatchingCandidatesResponse(BaseModel):
    need_id: uuid.UUID | None
    need_title: str | None
    total: int
    candidates: list[CandidateMatchItem]
