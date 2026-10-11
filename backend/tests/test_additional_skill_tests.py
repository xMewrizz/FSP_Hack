from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient

from app.core.additional_skill_bank import ADDITIONAL_SKILLS, ADDITIONAL_ALTERNATES, validate_additional_bank
from app.models.test import TestSession as CandidateTestSession
from conftest import TestingSessionLocal


async def candidate(client: AsyncClient, email: str, specialization: str) -> dict[str, str]:
    registered = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "role": "candidate",
    })
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": email, "code": registered.json()["verification_code"],
    })
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post("/api/v1/candidates/onboarding", headers=headers, json={
        "first_name": "Мария", "last_name": "Иванова", "city": "Москва",
        "specialization": specialization, "declared_grade": "junior", "agreed_152_fz": True,
    })
    assert onboarded.status_code == 200
    consent = await client.put("/api/v1/candidates/profile", headers=headers, json={"agreed_test_confidentiality": True})
    assert consent.status_code == 200
    return headers


def answers_for(skill: str, questions: list[dict], correct_count: int, open_text: str = "Практическое решение") -> list[dict]:
    by_code = {question["code"]: question for question in ADDITIONAL_SKILLS[skill]["questions"] + ADDITIONAL_ALTERNATES[skill]}
    answers = []
    selected_count = 0
    for question in questions:
        source = by_code[question["code"]]
        if question["question_type"] == "open_answer":
            answers.append({"question_id": question["id"], "answer_text": open_text})
        else:
            correct_text = next(option["text"] for option in source["options"] if option["id"] == source["correct_answers"][0])
            correct = next(option["id"] for option in question["options"] if option["text"] == correct_text)
            selected = correct if selected_count < correct_count else next(option["id"] for option in question["options"] if option["id"] != correct)
            answers.append({"question_id": question["id"], "selected_answers": [selected]})
            selected_count += 1
    return answers


@pytest.mark.asyncio
async def test_additional_catalog_and_weekly_retake_across_grades(client: AsyncClient):
    validate_additional_bank()
    headers = await candidate(client, "extra-grade-independent@example.com", "Backend")
    catalog = (await client.get("/api/v1/testing/additional", headers=headers)).json()
    assert {item["code"] for item in catalog} == {"git", "docker", "redis"}
    assert all(item["target_grade"] == "all" for item in catalog)

    start = await client.post("/api/v1/testing/additional/docker/start", headers=headers, json={"target_grade": "senior"})
    assert start.status_code == 201
    payload = start.json()
    assert payload["target_grade"] == "all"
    assert len(payload["questions"]) >= 5
    assert (await client.post("/api/v1/testing/additional/docker/start", headers=headers, json={})).json()["session_id"] == payload["session_id"]
    submitted = await client.post(f"/api/v1/testing/{payload['session_id']}/submit", headers=headers, json={
        "answers": answers_for("docker", payload["questions"], 4),
    })
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["percentage"] == 80.0
    assert submitted.json()["passed"] is True
    assert submitted.json()["verified_grade"] is None
    assert (await client.post("/api/v1/testing/additional/docker/start", headers=headers, json={})).status_code == 429
    profile = (await client.get("/api/v1/candidates/profile", headers=headers)).json()
    assert [item["code"] for item in profile["additional_skills"]] == ["docker"]

    async with TestingSessionLocal() as db:
        session = await db.get(CandidateTestSession, uuid.UUID(payload["session_id"]))
        session.completed_at = datetime.now(timezone.utc) - timedelta(days=8)
        await db.commit()
    retake = await client.post("/api/v1/testing/additional/docker/start", headers=headers, json={})
    assert retake.status_code == 201
    assert {item["code"] for item in retake.json()["questions"]}.isdisjoint({item["code"] for item in payload["questions"]})
    failed = await client.post(f"/api/v1/testing/{retake.json()['session_id']}/submit", headers=headers, json={
        "answers": answers_for("docker", retake.json()["questions"], 0),
    })
    assert failed.status_code == 200 and failed.json()["passed"] is False
    assert (await client.get("/api/v1/candidates/profile", headers=headers)).json()["additional_skills"][0]["percentage"] == 80.0
    available_after_failure = (await client.get("/api/v1/testing/additional", headers=headers)).json()
    docker = next(item for item in available_after_failure if item["code"] == "docker")
    assert docker["passed"] is True and docker["latest_percentage"] == 80.0


@pytest.mark.asyncio
async def test_open_answer_is_part_of_weighted_additional_test(client: AsyncClient, monkeypatch):
    headers = await candidate(client, "extra-open@example.com", "Data Science / ML")

    async def evaluate(_question, _answer):
        return {"score": 0.75, "passed": True, "feedback": "Подход верный, детали можно дополнить.",
                "criterion_scores": {}, "evaluator": "llm", "needs_manual_review": False}

    monkeypatch.setattr("app.services.open_question_service.evaluate_open_answer", evaluate)
    started = await client.post("/api/v1/testing/additional/data_preparation/start", headers=headers, json={})
    assert started.status_code == 201
    payload = started.json()
    assert len(payload["questions"]) == 5
    assert payload["questions"][-1]["question_type"] == "open_answer"
    assert payload["questions"][-1]["weight"] == 2
    answers = answers_for("data_preparation", payload["questions"], 3)
    incomplete = await client.post(f"/api/v1/testing/{payload['session_id']}/submit", headers=headers, json={"answers": answers[:-1]})
    assert incomplete.status_code == 400
    submitted = await client.post(f"/api/v1/testing/{payload['session_id']}/submit", headers=headers, json={"answers": answers})
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["score"] == 4.5 and result["max_score"] == 6.0
    assert result["percentage"] == 75.0 and result["passed"] is True
    assert result["question_review"][-1]["selected_answers"] == ["Практическое решение"]
    assert "Подход верный" in result["question_review"][-1]["explanation"]
    stored = (await client.get(f"/api/v1/testing/{payload['session_id']}", headers=headers)).json()
    assert stored["question_review"][-1]["selected_answers"] == ["Практическое решение"]
    assert (await client.get("/api/v1/candidates/profile", headers=headers)).json()["additional_skills"][0]["code"] == "data_preparation"


@pytest.mark.asyncio
async def test_unavailable_open_evaluation_does_not_fail_attempt(client: AsyncClient, monkeypatch):
    headers = await candidate(client, "extra-retry-eval@example.com", "Backend")

    async def unavailable(_question, _answer):
        return {"score": 0.0, "feedback": "", "evaluator": "fallback_heuristic", "needs_manual_review": True}

    monkeypatch.setattr("app.services.open_question_service.evaluate_open_answer", unavailable)
    started = (await client.post("/api/v1/testing/additional/redis/start", headers=headers, json={})).json()
    submitted = await client.post(f"/api/v1/testing/{started['session_id']}/submit", headers=headers, json={
        "answers": answers_for("redis", started["questions"], 4),
    })
    assert submitted.status_code == 503
    assert (await client.post("/api/v1/testing/additional/redis/start", headers=headers, json={})).json()["session_id"] == started["session_id"]
