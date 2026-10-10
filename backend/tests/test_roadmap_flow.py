import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy import select

from app.core.question_variants import prepared_variants
from app.models.candidate import CandidateProfile
from app.models.test import GradeAssessment
from conftest import TestingSessionLocal
from open_assessment_helpers import finish_open_assessment


async def candidate(client: AsyncClient, email: str, grade: str = "junior", specialization: str = "Backend") -> dict[str, str]:
    registered = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "role": "candidate",
    })
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": email, "code": registered.json()["verification_code"],
    })
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post("/api/v1/candidates/onboarding", headers=headers, json={
        "first_name": "Иван", "last_name": "Иванов", "city": "Москва",
        "specialization": specialization, "declared_grade": grade, "agreed_152_fz": True,
    })
    assert onboarded.status_code == 200
    return headers


async def finish_skill(client, headers, assessment_id, code, correct_count):
    started = await client.post(
        f"/api/v1/testing/roadmap/{assessment_id}/skills/{code}/start", headers=headers,
    )
    assert started.status_code == 201, started.text
    questions = started.json()["questions"]
    assert len(questions) == 10
    answers = []
    for index, question in enumerate(questions):
        base_code = question["code"].split("-V")[0]
        variant = next(item for item in prepared_variants(base_code) if item["code"] == question["code"])
        correct = variant["correct_answers"][0]
        selected = correct if index < correct_count else next(
            option["id"] for option in question["options"] if option["id"] != correct
        )
        answers.append({"question_id": question["id"], "selected_answers": [selected]})
    submitted = await client.post(
        f"/api/v1/testing/{started.json()['session_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


@pytest.mark.asyncio
async def test_roadmap_assigns_grade_only_after_four_skills_and_open_answers(client: AsyncClient):
    headers = await candidate(client, "roadmap-success@example.com")
    created = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert created.status_code == 201, created.text
    roadmap = created.json()
    assert [item["code"] for item in roadmap["skills"]] == ["backend_python", "sql", "api", "reliability"]
    assessment_id = roadmap["id"]

    for code, score in zip(("backend_python", "sql", "api", "reliability"), (10, 7, 7, 6)):
        result = await finish_skill(client, headers, assessment_id, code, score)
        if code != "reliability":
            assert result["grade_confirmed"] is False
            assert result["verified_grade"] is None
    assert result["grade_confirmed"] is False
    assert result["verified_grade"] is None
    await finish_open_assessment(assessment_id, (1.0, 0.5))

    stored_skill = await client.get(f"/api/v1/testing/{result['session_id']}", headers=headers)
    assert stored_skill.status_code == 200
    assert stored_skill.json()["grade_confirmed"] is True
    assert stored_skill.json()["required_correct"] == 5

    complete = await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)
    assert complete.status_code == 200
    assert complete.json()["percentage"] == 75.0
    assert complete.json()["passed"] is True
    assert [item["level_out_of_ten"] for item in complete.json()["skills"]] == [10.0, 7.0, 7.0, 6.0]
    assert [item["status"] for item in complete.json()["open_questions"]] == ["completed", "completed"]


@pytest.mark.asyncio
@pytest.mark.parametrize("grade", ("junior", "middle", "senior"))
async def test_data_science_full_roadmap_has_six_skills_and_open_work(client: AsyncClient, grade: str):
    headers = await candidate(client, f"ds-roadmap-{grade}@example.com", grade, "Data Science / ML")
    created = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert created.status_code == 201, created.text
    roadmap = created.json()
    assert roadmap["specialization"] == "Data Science / ML"
    assert roadmap["programming_language"] == "Python"
    assert len(roadmap["skills"]) == 6
    assert len(roadmap["open_questions"]) == (2 if grade == "junior" else 3)
    assert any(item["question_type"] == "code" for item in roadmap["open_questions"])
    if grade != "junior":
        assert any("WORK" in item["code"] for item in roadmap["open_questions"])
    for skill in roadmap["skills"]:
        await finish_skill(client, headers, roadmap["id"], skill["code"], 10)
    pending = (await client.get(f"/api/v1/testing/roadmap/{roadmap['id']}", headers=headers)).json()
    assert pending["verified_grade"] is None
    await finish_open_assessment(roadmap["id"])
    complete = (await client.get(f"/api/v1/testing/roadmap/{roadmap['id']}", headers=headers)).json()
    assert complete["verified_grade"] == grade
    assert complete["percentage"] == 100.0


@pytest.mark.asyncio
@pytest.mark.parametrize("specialization", ("Backend", "Data Science / ML"))
@pytest.mark.parametrize("grade", ("junior", "middle", "senior"))
async def test_full_retake_uses_other_open_tasks(client: AsyncClient, specialization: str, grade: str):
    headers = await candidate(client, f"retake-{specialization[:2]}-{grade}@example.com", grade, specialization)
    first = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    await finish_skill(client, headers, first["id"], first["skills"][0]["code"], 3)
    second = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    assert len(first["open_questions"]) == len(second["open_questions"])
    assert not {item["code"] for item in first["open_questions"]} & {item["code"] for item in second["open_questions"]}
    async with TestingSessionLocal() as db:
        original = await db.get(GradeAssessment, uuid.UUID(first["id"]))
        retake = await db.get(GradeAssessment, uuid.UUID(second["id"]))
        for skill in original.required_skills:
            first_texts = {item["question_text"] for item in original.question_snapshots[skill]}
            second_texts = {item["question_text"] for item in retake.question_snapshots[skill]}
            assert len(first_texts) == len(second_texts) == 10
            assert not first_texts & second_texts


@pytest.mark.asyncio
async def test_one_weak_skill_blocks_grade_even_when_overall_above_75(client: AsyncClient):
    headers = await candidate(client, "roadmap-weak@example.com", "middle")
    created = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    for code, score in zip(("backend_python", "sql", "api", "reliability"), (10, 10, 10, 4)):
        result = await finish_skill(client, headers, assessment_id, code, score)
    assert result["grade_confirmed"] is False
    assert result["suggested_grade"] is None
    complete = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert complete["status"] == "completed"
    assert complete["stopped_early"] is True
    assert complete["failed_skill"] == complete["skills"][-1]["label"]
    assert complete["percentage"] is None
    assert complete["passed"] is False
    assert complete["retake_used"] is False

    one_skill_again = await client.post(
        f"/api/v1/testing/roadmap/{assessment_id}/skills/reliability/start", headers=headers,
    )
    assert one_skill_again.status_code == 409
    retake = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    assert retake["id"] != assessment_id
    assert retake["retake_used"] is True
    assert all(skill["status"] == "not_started" for skill in retake["skills"])
    async with TestingSessionLocal() as db:
        original = await db.get(GradeAssessment, uuid.UUID(assessment_id))
        second = await db.get(GradeAssessment, uuid.UUID(retake["id"]))
        assert second.retake_of_id == original.id
        assert second.question_snapshots == original.retake_question_snapshots
    for skill in retake["skills"]:
        result = await finish_skill(client, headers, retake["id"], skill["code"], 10)
    assert result["grade_confirmed"] is False
    await finish_open_assessment(retake["id"])
    assert (await client.get("/api/v1/candidates/profile", headers=headers)).json()["verified_grade"] == "middle"


@pytest.mark.asyncio
async def test_only_one_full_retake_is_allowed(client: AsyncClient):
    headers = await candidate(client, "single-retake@example.com")
    roadmap = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    failed = await finish_skill(client, headers, roadmap["id"], "backend_python", 3)
    assert "Набор завершён досрочно" in failed["feedback"]
    remaining = await client.post(
        f"/api/v1/testing/roadmap/{roadmap['id']}/skills/sql/start", headers=headers,
    )
    assert remaining.status_code == 409
    assert (await client.get(f"/api/v1/testing/roadmap/{roadmap['id']}", headers=headers)).json()["stopped_early"] is True

    second = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    assert second["id"] != roadmap["id"]
    assert (await client.get(f"/api/v1/testing/roadmap/{roadmap['id']}", headers=headers)).json()["retake_used"] is True
    await finish_skill(client, headers, second["id"], "backend_python", 1)
    third = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert third.status_code == 409
    assert "через неделю" in third.json()["detail"]
    status = (await client.get(f"/api/v1/testing/roadmap/{second['id']}", headers=headers)).json()
    assert status["retry_available_at"] is not None
    async with TestingSessionLocal() as db:
        stored = await db.get(GradeAssessment, uuid.UUID(second["id"]))
        stored.completed_at = datetime.now(timezone.utc) - timedelta(days=8)
        await db.commit()
    next_cycle = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert next_cycle.status_code == 201
    assert next_cycle.json()["id"] != second["id"]
    assert next_cycle.json()["retake_used"] is False


@pytest.mark.asyncio
async def test_existing_open_roadmap_with_weak_skill_is_closed_on_refresh(client: AsyncClient):
    headers = await candidate(client, "legacy-weak@example.com", "senior")
    roadmap = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    await finish_skill(client, headers, roadmap["id"], "backend_python", 3)
    async with TestingSessionLocal() as db:
        stored = await db.get(GradeAssessment, uuid.UUID(roadmap["id"]))
        stored.status = "in_progress"
        stored.completed_at = None
        await db.commit()

    refreshed = await client.get("/api/v1/testing/roadmap/current", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "completed"
    assert refreshed.json()["stopped_early"] is True
    assert refreshed.json()["failed_skill"] == refreshed.json()["skills"][0]["label"]


@pytest.mark.asyncio
async def test_lower_grade_is_suggested_after_failed_full_retake(client: AsyncClient):
    headers = await candidate(client, "lower-after-weak@example.com", "middle")
    middle = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    failed = await finish_skill(client, headers, middle["id"], "backend_python", 1)
    assert failed["suggested_grade"] is None
    second = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    failed = await finish_skill(client, headers, second["id"], "backend_python", 1)
    assert failed["suggested_grade"] == "junior"
    assert (await client.get(f"/api/v1/testing/roadmap/{second['id']}", headers=headers)).json()["suggested_grade"] == "junior"
    lower = await client.post(
        "/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"},
    )
    assert lower.status_code == 201
    assert lower.json()["target_grade"] == "junior"
    for skill in lower.json()["skills"]:
        await finish_skill(client, headers, lower.json()["id"], skill["code"], 10)
    await finish_open_assessment(lower.json()["id"])
    async with TestingSessionLocal() as db:
        profile = await db.scalar(select(CandidateProfile))
        profile.verified_grade_updated_at = datetime.now(timezone.utc) - timedelta(days=91)
        for assessment_id in (middle["id"], second["id"]):
            old = await db.get(GradeAssessment, uuid.UUID(assessment_id))
            old.created_at = datetime.now(timezone.utc) - timedelta(days=100)
        await db.commit()
    promoted = await client.post(
        "/api/v1/testing/roadmap", headers=headers, json={"target_grade": "middle"},
    )
    assert promoted.status_code == 201, promoted.text
    assert promoted.json()["retake_used"] is False


@pytest.mark.asyncio
async def test_roadmap_freezes_questions_and_expires_after_three_days(client: AsyncClient):
    headers = await candidate(client, "frozen-roadmap@example.com")
    roadmap = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    async with TestingSessionLocal() as db:
        stored = await db.get(GradeAssessment, uuid.UUID(roadmap["id"]))
        frozen = stored.question_snapshots["sql"]
        assert len(frozen) == 10
        assert stored.retake_question_snapshots["sql"][0]["code"] != frozen[0]["code"]

    started = await client.post(
        f"/api/v1/testing/roadmap/{roadmap['id']}/skills/sql/start", headers=headers,
    )
    assert started.status_code == 201
    assert [item["id"] for item in started.json()["questions"]] == [item["id"] for item in frozen]

    async with TestingSessionLocal() as db:
        stored = await db.get(GradeAssessment, uuid.UUID(roadmap["id"]))
        stored.created_at = datetime.now(timezone.utc) - timedelta(days=4)
        await db.commit()
    expired = await client.get(f"/api/v1/testing/roadmap/{roadmap['id']}", headers=headers)
    assert expired.json()["status"] == "expired"
    blocked = await client.post(
        f"/api/v1/testing/roadmap/{roadmap['id']}/skills/backend_python/start", headers=headers,
    )
    assert blocked.status_code == 409
    restarted = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert restarted.status_code == 201
    assert restarted.json()["id"] != roadmap["id"]


@pytest.mark.asyncio
async def test_additional_git_result_is_separate_from_grade(client: AsyncClient):
    headers = await candidate(client, "additional-git@example.com")
    available = await client.get("/api/v1/testing/additional", headers=headers)
    assert available.status_code == 200
    assert available.json() == []
    before_grade = await client.post(
        "/api/v1/testing/additional/git/start", headers=headers,
        json={"target_grade": "junior"},
    )
    assert before_grade.status_code == 409

    roadmap = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    for skill in roadmap["skills"]:
        await finish_skill(client, headers, roadmap["id"], skill["code"], 10)
    await finish_open_assessment(roadmap["id"])
    available = await client.get("/api/v1/testing/additional", headers=headers)
    assert [(item["code"], item["target_grade"]) for item in available.json()] == [("git", "junior")]

    unsupported = await client.post(
        "/api/v1/testing/additional/docker/start", headers=headers,
        json={"target_grade": "junior"},
    )
    assert unsupported.status_code == 400

    started = await client.post(
        "/api/v1/testing/additional/git/start", headers=headers,
        json={"target_grade": "junior"},
    )
    assert started.status_code == 201
    questions = started.json()["questions"]
    assert len(questions) == 3
    answers = []
    for question in questions:
        variant = next(item for item in prepared_variants(question["code"].split("-V")[0]) if item["code"] == question["code"])
        answers.append({"question_id": question["id"], "selected_answers": variant["correct_answers"]})
    submitted = await client.post(
        f"/api/v1/testing/{started.json()['session_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert submitted.status_code == 200
    assert submitted.json()["passed"] is None
    assert submitted.json()["grade_confirmed"] is False
    assert submitted.json()["verified_grade"] == "junior"

    available_after = await client.get("/api/v1/testing/additional", headers=headers)
    assert available_after.json()[0]["level_out_of_ten"] == 10.0
    assert (await client.get("/api/v1/testing/roadmap/current", headers=headers)).json()["id"] == roadmap["id"]


@pytest.mark.asyncio
async def test_changing_specialization_clears_grade_and_cancels_current_roadmap(client: AsyncClient):
    headers = await candidate(client, "change-specialization@example.com")
    created = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assessment_id = created.json()["id"]
    await finish_skill(client, headers, assessment_id, "backend_python", 10)
    changed = await client.put(
        "/api/v1/candidate/profile", headers=headers,
        json={"specialization": "Frontend"},
    )
    assert changed.status_code == 200
    assert changed.json()["verified_grade"] is None
    assert (await client.get("/api/v1/testing/roadmap/current", headers=headers)).json() is None
    old = await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)
    assert old.json()["status"] == "cancelled"
    rejected = await client.post(
        "/api/v1/testing/roadmap", headers=headers,
        json={"specialization": "Backend", "target_grade": "junior"},
    )
    assert rejected.status_code == 400


@pytest.mark.asyncio
async def test_promotion_uses_full_next_grade_and_90_day_rule(client: AsyncClient):
    headers = await candidate(client, "promotion@example.com")
    junior = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    for skill in junior["skills"]:
        result = await finish_skill(client, headers, junior["id"], skill["code"], 10)
    assert result["verified_grade"] is None
    await finish_open_assessment(junior["id"])

    too_early = await client.post(
        "/api/v1/testing/roadmap", headers=headers,
        json={"target_grade": "middle"},
    )
    assert too_early.status_code == 400
    jump = await client.post(
        "/api/v1/testing/roadmap", headers=headers,
        json={"target_grade": "senior"},
    )
    assert jump.status_code == 400

    async with TestingSessionLocal() as db:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.first_name == "Иван"))
        profile.verified_grade_updated_at = datetime.now(timezone.utc) - timedelta(days=91)
        await db.commit()

    middle = await client.post(
        "/api/v1/testing/roadmap", headers=headers,
        json={"target_grade": "middle"},
    )
    assert middle.status_code == 201
    assert [item["status"] for item in middle.json()["skills"]] == ["not_started"] * 4
    for skill in middle.json()["skills"]:
        result = await finish_skill(client, headers, middle.json()["id"], skill["code"], 10)
    assert result["verified_grade"] == "junior"
    await finish_open_assessment(middle.json()["id"])
    assert (await client.get("/api/v1/candidates/profile", headers=headers)).json()["verified_grade"] == "middle"


@pytest.mark.asyncio
async def test_cannot_start_two_grade_roadmaps_at_once(client: AsyncClient):
    headers = await candidate(client, "one-roadmap@example.com")
    junior = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert junior.status_code == 201
    resumed = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert resumed.status_code == 201
    assert resumed.json()["id"] == junior.json()["id"]

    middle = await client.post(
        "/api/v1/testing/roadmap", headers=headers, json={"target_grade": "middle"},
    )
    assert middle.status_code == 409
    assert "завершите" in middle.json()["detail"]


@pytest.mark.asyncio
async def test_same_grade_retake_does_not_restart_promotion_wait(client: AsyncClient):
    headers = await candidate(client, "same-grade-retake@example.com")
    first = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    for skill in first["skills"]:
        await finish_skill(client, headers, first["id"], skill["code"], 10)
    await finish_open_assessment(first["id"])

    async with TestingSessionLocal() as db:
        profile = await db.scalar(select(CandidateProfile))
        original_date = datetime.now(timezone.utc) - timedelta(days=91)
        profile.verified_grade_updated_at = original_date
        await db.commit()

    retake = (await client.post("/api/v1/testing/roadmap", headers=headers, json={})).json()
    assert retake["id"] != first["id"]
    assert retake["retake_used"] is True
    for skill in retake["skills"]:
        await finish_skill(client, headers, retake["id"], skill["code"], 10)
    await finish_open_assessment(retake["id"])

    async with TestingSessionLocal() as db:
        profile = await db.scalar(select(CandidateProfile))
        saved_date = profile.verified_grade_updated_at
        if saved_date.tzinfo is None:
            saved_date = saved_date.replace(tzinfo=timezone.utc)
        assert saved_date == original_date

    promotion = await client.post(
        "/api/v1/testing/roadmap", headers=headers, json={"target_grade": "middle"},
    )
    assert promotion.status_code == 201, promotion.text
