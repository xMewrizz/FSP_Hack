from datetime import datetime, timedelta, timezone
import pytest
from app.models.candidate import CandidateProfile
from app.models.fsp import FSPAchievement
from app.models.test import TestSession

TestSession.__test__ = False
from app.services.trust_score_service import calculate_trust_score

def test_trust_score_high():
    now = datetime.now(timezone.utc)
    candidate = CandidateProfile(
        first_name="Test",
        last_name="Testov",
        verified_grade="Middle",
        fsp_verified=True,
        bio="Hello I am test",
        skills=["Python", "FastAPI"],
        city="Moscow",
        work_format="remote",
        last_active_at=now,
        resume_text="I worked at some place.\nPython developer.\n2018-2022 Company Alphabet",
    )
    
    achievement = FSPAchievement(verified=True)
    candidate.fsp_achievements = [achievement]
    
    session = TestSession(passed=True)
    candidate.test_sessions = [session]
    
    score, flags = calculate_trust_score(candidate)
    
    assert 0.8 <= score <= 1.0
    assert all(flag["status"] == "verified" for flag in flags)

def test_trust_score_low():
    candidate = CandidateProfile(
        first_name="Test2",
        last_name="Testov2",
        fsp_verified=False,
    )
    candidate.fsp_achievements = []
    candidate.test_sessions = []
    
    score, flags = calculate_trust_score(candidate)
    
    assert score == 0.0
    assert all(flag["status"] == "review" for flag in flags)

def test_trust_score_warnings():
    now = datetime.now(timezone.utc)
    candidate = CandidateProfile(
        first_name="Test",
        last_name="Testov",
        verified_grade="Middle",
        fsp_verified=False,
        bio="Hello I am test",
        skills=["Python"],
        city="Moscow",
        work_format="remote",
        last_active_at=now,
        resume_text="Worked 1900-2024 at Company B", # Impossible dates
    )
    candidate.fsp_achievements = []
    candidate.test_sessions = []
    
    score, flags = calculate_trust_score(candidate)
    
    resume_flag = next(f for f in flags if f["label"] == "Резюме")
    assert resume_flag["status"] == "warning"
    assert score > 0.0 # gets points for profile and verified grade
    assert score < 1.0

def test_score_bounds():
    now = datetime.now(timezone.utc)
    candidate = CandidateProfile(
        first_name="Test",
        last_name="Testov",
        verified_grade="Middle",
        fsp_verified=True,
        bio="Hello I am test",
        skills=["Python", "FastAPI"],
        city="Moscow",
        work_format="remote",
        last_active_at=now,
        resume_text="Normal resume without errors.\n2020-2023 Company Alphabet",
    )
    achievement = FSPAchievement(verified=True)
    candidate.fsp_achievements = [achievement]
    session = TestSession(passed=True)
    candidate.test_sessions = [session]
    
    score, flags = calculate_trust_score(candidate)
    assert 0.0 <= score <= 1.0
