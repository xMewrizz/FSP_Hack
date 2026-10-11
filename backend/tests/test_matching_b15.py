"""Проверка выдачи работодателя и связи API с формулой B-14."""

import pytest
from httpx import AsyncClient

from app.core.constants import UserRole
from app.core.ranking import rank_candidates
from app.core.security import create_access_token
from app.models.candidate import CandidateProfile
from app.models.candidate_specialization import CandidateSpecializationTrack
from app.models.employer import EmployerProfile
from app.models.need import EmployerNeed
from app.models.test import GradeAssessment, TestSession as CandidateTestSession
from app.models.user import User
from conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_each_verified_specialization_is_searchable_and_matchable(client: AsyncClient):
    async with TestingSessionLocal() as db:
        employer_user = User(email="multi-track-owner@example.test", hashed_password="unused", role=UserRole.EMPLOYER, is_verified=True)
        candidate_user = User(email="multi-track-candidate@example.test", hashed_password="unused", role=UserRole.CANDIDATE, is_verified=True)
        db.add_all([employer_user, candidate_user])
        await db.flush()
        employer = EmployerProfile(user_id=employer_user.id, company_name="Компания", onboarding_completed=True)
        profile = CandidateProfile(
            user_id=candidate_user.id, first_name="Мария", last_name="Тестовая",
            specialization="Backend", verified_specialization="Backend",
            declared_grade="junior", verified_grade="junior",
            skills=["Python", "Pandas"], work_format="remote",
            onboarding_completed=True, agreed_publication=True, visibility_public=True,
        )
        db.add_all([employer, profile])
        await db.flush()
        need = EmployerNeed(
            employer_id=employer.id, title="Data Scientist Middle", specialization="Data Science / ML",
            required_grade="middle", required_skills=[{"name": "Pandas", "weight": 5}],
            salary_min=100000, salary_max=300000, salary_tax_type="gross", work_format="remote",
        )
        track = CandidateSpecializationTrack(
            candidate_profile_id=profile.id, specialization="Data Science / ML",
            declared_grade="middle", verified_grade="middle",
        )
        db.add_all([need, track])
        await db.flush()
        assessment = GradeAssessment(
            user_id=candidate_user.id, candidate_profile_id=profile.id,
            specialization="Data Science / ML", target_grade="middle",
            required_skills=[], question_codes={}, question_snapshots={}, retake_question_snapshots={},
            scoring_policy={}, status="completed", passed=True, percentage=88,
        )
        db.add(assessment)
        await db.flush()
        db.add(CandidateTestSession(
            user_id=candidate_user.id, candidate_profile_id=profile.id,
            assessment_id=assessment.id, specialization="Data Science / ML", target_grade="middle",
            skill_code="ds_pandas", status="completed", percentage=90,
        ))
        await db.commit()
        need_id, employer_id, candidate_id = need.id, employer_user.id, profile.id

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(employer_id)})}"}
    matched = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=headers)
    assert matched.status_code == 200, matched.text
    assert matched.json()["total"] == 1
    item = matched.json()["candidates"][0]
    assert item["candidate_id"] == str(candidate_id)
    assert (item["specialization"], item["verified_grade"], item["test_percentage"]) == ("Data Science / ML", "middle", 88)
    assert item["requested_skill_tests"][0]["percentage"] == 90
    assert "Data Science / ML" in item["match_explanation"]["summary"]

    search = await client.get("/api/v1/matching/search?specialization=Data%20Science%20%2F%20ML&grade=middle", headers=headers)
    assert search.status_code == 200, search.text
    assert [(row["candidate_id"], row["specialization"], row["verified_grade"]) for row in search.json()] == [
        (str(candidate_id), "Data Science / ML", "middle")
    ]
    backend_search = await client.get("/api/v1/matching/search?specialization=Backend&grade=junior", headers=headers)
    assert backend_search.status_code == 200
    assert backend_search.json()[0]["candidate_id"] == str(candidate_id)


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
            required_grade="middle", required_skills=[
                {"name": "Python", "weight": 5}, {"name": "SQL", "weight": 4},
                {"name": "HTTP API", "weight": 4}, {"name": "Git", "weight": 2},
                {"name": "Docker", "weight": 1}, {"name": "FastAPI", "weight": 1},
                {"name": "PostgreSQL", "weight": 1},
            ],
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
                assessment = GradeAssessment(
                    user_id=user.id, candidate_profile_id=profile.id,
                    specialization=specialization, target_grade=grade,
                    required_skills=[], question_codes={}, question_snapshots={},
                    retake_question_snapshots={}, scoring_policy={}, status="completed",
                    passed=True, percentage=percentage,
                )
                db.add(assessment)
                await db.flush()
                if index == 0:
                    for code, result in (("backend_python", 80), ("sql", 60), ("api", 90)):
                        db.add(CandidateTestSession(
                            user_id=user.id, candidate_profile_id=profile.id,
                            assessment_id=assessment.id, specialization="Backend",
                            target_grade="middle", skill_code=code,
                            status="completed", percentage=result,
                        ))
                    db.add(CandidateTestSession(
                        user_id=user.id, candidate_profile_id=profile.id,
                        specialization="Backend", target_grade="all", skill_code="git",
                        status="completed", percentage=80, passed=True,
                    ))
                    db.add(CandidateTestSession(
                        user_id=user.id, candidate_profile_id=profile.id,
                        specialization="Backend", target_grade="junior", skill_code="git",
                        status="completed", percentage=99, passed=False,
                    ))
                    failed_assessment = GradeAssessment(
                        user_id=user.id, candidate_profile_id=profile.id,
                        specialization="Backend", target_grade="middle",
                        required_skills=[], question_codes={}, question_snapshots={},
                        retake_question_snapshots={}, scoring_policy={}, status="completed",
                        passed=False, percentage=100,
                    )
                    db.add(failed_assessment)
                    await db.flush()
                    db.add(CandidateTestSession(
                        user_id=user.id, candidate_profile_id=profile.id,
                        assessment_id=failed_assessment.id, specialization="Backend",
                        target_grade="middle", skill_code="backend_python",
                        status="completed", percentage=100,
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
                 "salary_tax_type": "gross", "fsp_verified": False, "fsp_achievements": [],
                 "requested_skill_tests": (
                     [{"name": name, "percentage": result} for name, result in
                         (("Python", 80), ("SQL", 60), ("HTTP API", 90), ("Git", 80))]
                     if profile.id == profiles[0].id else []
                 )}
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
    assert data["candidates"][0]["candidate_id"] == str(profiles[0].id)
    assert "Отдельные результаты тестов есть по 4 из 7" in data["candidates"][0]["match_explanation"]["summary"]
    assert all(item["match_explanation"]["grade_match"] for item in data["candidates"])
    assert all(item["match_explanation"]["summary"] for item in data["candidates"])
    skill_tests = next(item for item in data["candidates"] if item["candidate_id"] == str(profiles[0].id))["requested_skill_tests"]
    assert [(item["name"], item["percentage"], item["test_kind"]) for item in skill_tests] == [
        ("Python", 80, "base"), ("SQL", 60, "base"),
        ("HTTP API", 90, "base"), ("Git", 80, "additional"),
        ("Docker", None, None), ("FastAPI", None, None),
        ("PostgreSQL", None, None),
    ]
    assert all(item["percentage"] is None for item in next(
        item for item in data["candidates"] if item["candidate_id"] == str(profiles[1].id)
    )["requested_skill_tests"])

    search = await client.get("/api/v1/matching/search?specialization=Backend&grade=middle", headers=headers)
    assert search.status_code == 200
    assert {item["candidate_id"] for item in search.json()} == expected_ids
    stack_search = await client.get("/api/v1/matching/search?specialization=Backend&grade=middle&skill=doc", headers=headers)
    assert stack_search.status_code == 200
    assert {item["candidate_id"] for item in stack_search.json()} == {str(profiles[0].id)}
    empty_stack_search = await client.get("/api/v1/matching/search?skill=Rust", headers=headers)
    assert empty_stack_search.status_code == 200
    assert empty_stack_search.json() == []
    forbidden = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=other_headers)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_data_science_skill_results_appear_in_matching_and_affect_order(client: AsyncClient):
    async with TestingSessionLocal() as db:
        owner = User(email="ds-match-owner@example.test", hashed_password="unused", role=UserRole.EMPLOYER, is_verified=True)
        db.add(owner)
        await db.flush()
        employer = EmployerProfile(user_id=owner.id, company_name="Компания", onboarding_completed=True)
        db.add(employer)
        await db.flush()
        need = EmployerNeed(
            employer_id=employer.id, title="Data Scientist", specialization="Data Science / ML",
            required_grade="senior", required_skills=[
                {"name": "Python", "weight": 5}, {"name": "Pandas", "weight": 4},
                {"name": "SQL", "weight": 4}, {"name": "Machine Learning", "weight": 5},
                {"name": "Docker", "weight": 2},
            ],
            salary_min=300000, salary_max=450000, salary_tax_type="gross", work_format="remote",
        )
        db.add(need)
        await db.flush()
        profiles = []
        for index in range(2):
            user = User(email=f"ds-match-{index}@example.test", hashed_password="unused", role=UserRole.CANDIDATE, is_verified=True)
            db.add(user)
            await db.flush()
            profile = CandidateProfile(
                user_id=user.id, first_name="Кандидат", last_name=str(index),
                specialization="Data Science / ML", verified_specialization="Data Science / ML",
                declared_grade="senior", verified_grade="senior",
                skills=["Python", "Pandas", "SQL", "машинное обучение", "Docker"],
                work_format="remote", salary_expectation=400000, salary_tax_type="gross",
                onboarding_completed=True, agreed_publication=True, visibility_public=True,
            )
            db.add(profile)
            await db.flush()
            assessment = GradeAssessment(
                user_id=user.id, candidate_profile_id=profile.id,
                specialization="Data Science / ML", target_grade="senior",
                required_skills=[], question_codes={}, question_snapshots={},
                retake_question_snapshots={}, scoring_policy={}, status="completed",
                passed=True, percentage=85,
            )
            db.add(assessment)
            await db.flush()
            if index == 0:
                for code, percentage in (("ds_python", 90), ("ds_pandas", 80), ("ds_sql", 90), ("ds_ml", 80)):
                    db.add(CandidateTestSession(
                        user_id=user.id, candidate_profile_id=profile.id,
                        assessment_id=assessment.id, specialization="Data Science / ML",
                        target_grade="senior", skill_code=code,
                        status="completed", percentage=percentage,
                    ))
            profiles.append(profile)
        await db.commit()
        need_id, owner_id = need.id, owner.id
        tested_id, untested_id = (str(profile.id) for profile in profiles)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(owner_id)})}"}
    response = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["candidates"]
    assert [item["candidate_id"] for item in data] == [tested_id, untested_id]
    assert [(item["name"], item["percentage"]) for item in data[0]["requested_skill_tests"]] == [
        ("Python", 90), ("Pandas", 80), ("SQL", 90), ("Machine Learning", 80), ("Docker", None),
    ]
    assert "4 из 5 запрошенных навыков" in data[0]["match_explanation"]["summary"]
    assert "машинное обучение" in data[0]["match_explanation"]["matched_skills"]
    assert "машинное обучение" not in data[0]["match_explanation"]["missing_skills"]
