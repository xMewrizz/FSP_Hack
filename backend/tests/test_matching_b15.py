"""Проверка выдачи работодателя и связи API с формулой B-14."""

import pytest
from httpx import AsyncClient

from app.core.constants import UserRole
from app.core.ranking import rank_candidates
from app.core.security import create_access_token
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.need import EmployerNeed
from app.models.test import GradeAssessment
from app.models.user import User
from conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_matching_only_confirmed_and_order_matches_b14(client: AsyncClient):
    async with TestingSessionLocal() as db:
        owner = User(email="b15-owner@example.test", hashed_password="unused", role=UserRole.EMPLOYER, is_verified=True)
        outsider = User(email="b15-other@example.test", hashed_password="unused", role=UserRole.EMPLOYER, is_verified=True)
        db.add_all([owner, outsider])
        await db.flush()
        employer = EmployerProfile(user_id=owner.id, company_name="Компания", onboarding_completed=True)
        db.add(employer)
        await db.flush()
        need = EmployerNeed(
            employer_id=employer.id, title="Backend Middle", specialization="Backend",
            required_grade="middle", required_skills=[{"name": "Python", "weight": 5}, {"name": "Docker", "weight": 1}],
            salary_min=180000, salary_max=260000, salary_tax_type="gross", work_format="remote",
        )
        db.add(need)
        await db.flush()

        profiles = []
        for index, (grade, specialization, visible, skills, percentage) in enumerate((
            ("middle", "Backend", True, ["Python", "Docker"], 90.0),
            ("middle", "Backend", True, ["Python"], 76.0),
            (None, "Backend", True, ["Python", "Docker"], None),
            ("junior", "Backend", True, ["Python", "Docker"], 99.0),
            ("middle", "Frontend", True, ["Python", "Docker"], 95.0),
            ("middle", "Backend", False, ["Python", "Docker"], 98.0),
        )):
            user = User(email=f"b15-{index}@example.test", hashed_password="unused", role=UserRole.CANDIDATE, is_verified=True)
            db.add(user)
            await db.flush()
            profile = CandidateProfile(
                user_id=user.id, first_name="Кандидат", last_name=str(index),
                specialization=specialization, verified_specialization=specialization if grade else None,
                declared_grade="middle", verified_grade=grade, skills=skills,
                work_format="remote", salary_expectation=220000, salary_tax_type="gross",
                onboarding_completed=True, agreed_publication=True, visibility_public=visible,
            )
            db.add(profile)
            await db.flush()
            profiles.append(profile)
            if percentage is not None and grade == "middle":
                db.add(GradeAssessment(
                    user_id=user.id, candidate_profile_id=profile.id,
                    specialization=specialization, target_grade=grade,
                    required_skills=[], question_codes={}, question_snapshots={},
                    retake_question_snapshots={}, scoring_policy={}, status="completed",
                    passed=True, percentage=percentage,
                ))
        await db.commit()
        need_id = need.id
        owner_id, outsider_id = owner.id, outsider.id
        expected_ids = {str(profiles[0].id), str(profiles[1].id)}
        expected = rank_candidates(
            {"specialization": "Backend", "required_grade": "middle", "required_skills": need.required_skills,
             "work_format": "remote", "salary_max": 260000, "salary_tax_type": "gross"},
            [
                {"id": profile.id, "specialization": "Backend", "verified_grade": "middle", "skills": profile.skills,
                 "test_percentage": percentage, "work_format": "remote", "salary_expectation": 220000,
                 "salary_tax_type": "gross", "fsp_verified": False, "fsp_achievements": []}
                for profile, percentage in ((profiles[0], 90.0), (profiles[1], 76.0))
            ],
        )

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(owner_id)})}"}
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(outsider_id)})}"}
    response = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert {item["candidate_id"] for item in data["candidates"]} == expected_ids
    assert [item["candidate_id"] for item in data["candidates"]] == [str(item["candidate_id"]) for item in expected]
    assert [item["match_score"] for item in data["candidates"]] == [item["points"] for item in expected]
    assert all(item["match_explanation"]["grade_match"] for item in data["candidates"])
    assert all(item["match_explanation"]["summary"] for item in data["candidates"])

    search = await client.get("/api/v1/matching/search?specialization=Backend&grade=middle", headers=headers)
    assert search.status_code == 200
    assert {item["candidate_id"] for item in search.json()} == expected_ids
    forbidden = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=other_headers)
    assert forbidden.status_code == 403
