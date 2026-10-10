import uuid

import pytest
from httpx import AsyncClient

from app.core.question_variants import BACKEND_FAMILIES, prepared_variants
from app.models.test import TestSession as SessionModel
from conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_retries_rotate_prepared_variants_and_save_answer_version(client: AsyncClient):
    email = "variants@example.com"
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "candidate"},
    )
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post(
        "/api/v1/candidate/onboarding", headers=headers,
        json={
            "first_name": "Иван", "last_name": "Иванов", "city": "Москва",
            "specialization": "Backend", "declared_grade": "junior", "agreed_152_fz": True,
        },
    )
    assert onboarded.status_code == 200
    consent = await client.put(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"agreed_test_confidentiality": True},
    )
    assert consent.status_code == 200

    attempts = []
    for expected_version in ("v1", "v2", "v3"):
        started = await client.post("/api/v1/testing/start", headers=headers, json={})
        assert started.status_code == 201
        attempt = started.json()
        assert len(attempt["questions"]) == 12
        assert all(
            question["code"] == prepared_variants(question["code"].split("-V")[0])[int(expected_version[1]) - 1]["code"]
            for question in attempt["questions"]
        )
        attempts.append(attempt)

    assert {q["id"] for q in attempts[0]["questions"]}.isdisjoint(
        {q["id"] for q in attempts[1]["questions"]}
    )
    fourth = await client.post("/api/v1/testing/start", headers=headers, json={})
    assert fourth.status_code == 201
    assert [q["code"] for q in fourth.json()["questions"]] == [
        q["code"] for q in attempts[0]["questions"]
    ]

    second = attempts[1]
    foreign_answer = {
        "question_id": attempts[0]["questions"][0]["id"], "selected_answers": ["A"],
    }
    rejected = await client.post(
        f"/api/v1/testing/{second['session_id']}/submit",
        headers=headers, json={"answers": [foreign_answer]},
    )
    assert rejected.status_code == 400

    correct = {
        variant["code"]: variant["correct_answers"]
        for code in BACKEND_FAMILIES if code.startswith("BE-JR-")
        for variant in prepared_variants(code)
    }
    answers = [
        {"question_id": question["id"], "selected_answers": correct[question["code"]]}
        for question in second["questions"]
    ]
    submitted = await client.post(
        f"/api/v1/testing/{second['session_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert submitted.status_code == 200
    assert submitted.json()["percentage"] == 100.0

    async with TestingSessionLocal() as db:
        session = await db.get(SessionModel, uuid.UUID(second["session_id"]))
        assert session is not None
        assert {q["variant_id"] for q in session.questions_snapshot} == {"v2"}
        assert {q["family_code"] for q in session.questions_snapshot} == {
            code for code in BACKEND_FAMILIES
            if code.startswith("BE-JR-") and int(code.split("-")[-1]) <= 12
        }
        assert all(q["correct_answers"] for q in session.questions_snapshot)
        assert {answer["variant_id"] for answer in session.answers_data} == {"v2"}
        assert [answer["question_id"] for answer in session.answers_data] == [
            answer["question_id"] for answer in answers
        ]
