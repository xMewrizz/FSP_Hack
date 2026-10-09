import pytest
import uuid
from httpx import AsyncClient
from app.core.question_variants import BACKEND_FAMILIES, prepared_variants


async def register_and_verify(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": role},
    )
    assert registered.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    assert verified.status_code == 200
    return {"Authorization": f"Bearer {verified.json()['access_token']}"}


@pytest.mark.asyncio
async def test_company_profile_edit_and_ownership(client: AsyncClient):
    first = await register_and_verify(client, "first-company@example.com", "employer")
    second = await register_and_verify(client, "second-company@example.com", "employer")
    candidate = await register_and_verify(client, "candidate-company@example.com", "candidate")

    created = await client.post(
        "/api/v1/employer/onboarding",
        headers=first,
        json={"company_name": "Первая компания", "contact_person": "Анна", "city": "Москва"},
    )
    assert created.status_code == 200
    await client.post(
        "/api/v1/employer/onboarding",
        headers=second,
        json={"company_name": "Вторая компания", "contact_person": "Борис", "city": "Казань"},
    )

    updated = await client.put(
        "/api/v1/employer/profile",
        headers=first,
        json={"description": "Разработка сервисов", "phone": "+79991234567", "city": "Тверь"},
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Тверь"
    assert updated.json()["description"] == "Разработка сервисов"
    assert updated.json()["phone"] == "+79991234567"

    own = await client.get("/api/v1/employer/profile", headers=second)
    assert own.status_code == 200
    assert own.json()["company_name"] == "Вторая компания"
    assert own.json()["city"] == "Казань"
    forbidden = await client.put(
        "/api/v1/employer/profile", headers=candidate, json={"company_name": "Чужая компания"}
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_invitation_rejection_and_foreign_record_access(client: AsyncClient):
    employer = await register_and_verify(client, "inviter@example.com", "employer")
    outsider_employer = await register_and_verify(client, "outsider@example.com", "employer")
    candidate = await register_and_verify(client, "invited@example.com", "candidate")
    outsider_candidate = await register_and_verify(client, "outsider-candidate@example.com", "candidate")

    await client.post(
        "/api/v1/employer/onboarding", headers=employer,
        json={"company_name": "Приглашающая компания", "contact_person": "Анна"},
    )
    await client.post(
        "/api/v1/employer/onboarding", headers=outsider_employer,
        json={"company_name": "Другая компания", "contact_person": "Борис"},
    )
    onboard = await client.post(
        "/api/v1/candidate/onboarding", headers=candidate,
        json={
            "first_name": "Иван", "last_name": "Иванов", "city": "Москва",
            "specialization": "Backend", "declared_grade": "junior",
            "agreed_152_fz": True, "agreed_publication": True, "visibility_public": True,
        },
    )
    assert onboard.status_code == 200
    foreign_need = await client.post(
        "/api/v1/needs", headers=outsider_employer,
        json={"title": "Backend Junior", "specialization": "Backend", "required_grade": "junior",
              "salary_min": 100000, "salary_max": 150000},
    )
    assert foreign_need.status_code == 201
    payload = {
        "candidate_id": onboard.json()["id"],
        "offer_description": "Приглашаем в команду разработки",
        "contact_method": "Telegram", "salary_min": 100000, "salary_max": 150000,
        "salary_tax_type": "net",
    }
    for need_id in (foreign_need.json()["id"], str(uuid.uuid4())):
        bad = await client.post("/api/v1/invitations", headers=employer,
                                json={**payload, "need_id": need_id})
        assert bad.status_code == 404
    assert (await client.get("/api/v1/invitations/my", headers=candidate)).json() == []
    invalid_currency = await client.post("/api/v1/invitations", headers=employer,
                                         json={**payload, "currency": "USD"})
    assert invalid_currency.status_code == 422
    invited = await client.post(
        "/api/v1/invitations", headers=employer,
        json=payload,
    )
    assert invited.status_code == 201
    assert invited.json()["salary_tax_type"] == "net"
    invitation_id = invited.json()["id"]
    assert invited.json()["candidate_contacts"] is None

    wrong_candidate = await client.post(
        f"/api/v1/invitations/{invitation_id}/reject", headers=outsider_candidate
    )
    assert wrong_candidate.status_code == 404
    other_invitations = await client.get("/api/v1/invitations/my", headers=outsider_candidate)
    assert other_invitations.status_code == 200
    assert other_invitations.json() == []
    assert (await client.get("/api/v1/invitations/sent", headers=outsider_employer)).json() == []

    rejected = await client.post(f"/api/v1/invitations/{invitation_id}/reject", headers=candidate)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    sent = await client.get("/api/v1/invitations/sent", headers=employer)
    assert sent.status_code == 200
    assert sent.json()[0]["status"] == "rejected"
    assert sent.json()[0]["salary_tax_type"] == "net"
    assert sent.json()[0]["candidate_contacts"] is None


@pytest.mark.asyncio
async def test_failed_retake_does_not_remove_verified_grade(client: AsyncClient):
    candidate = await register_and_verify(client, "grade-retake@example.com", "candidate")
    onboard = await client.post(
        "/api/v1/candidate/onboarding", headers=candidate,
        json={
            "first_name": "Иван", "last_name": "Тестовый", "city": "Москва",
            "specialization": "Backend", "declared_grade": "junior", "agreed_152_fz": True,
        },
    )
    assert onboard.status_code == 200
    assert onboard.json()["verified_grade"] is None

    first_attempt = await client.post("/api/v1/testing/start", headers=candidate, json={})
    assert first_attempt.status_code == 201
    first_failure = await client.post(
        f"/api/v1/testing/{first_attempt.json()['session_id']}/submit",
        headers=candidate, json={"answers": []},
    )
    assert first_failure.status_code == 200
    assert first_failure.json()["passed"] is False
    assert first_failure.json()["verified_grade"] is None

    correct = {
        variant["code"]: variant["correct_answers"][0]
        for code in BACKEND_FAMILIES if code.startswith("BE-JR-")
        for variant in prepared_variants(code)
    }
    roadmap = await client.post("/api/v1/testing/roadmap", headers=candidate, json={})
    assert roadmap.status_code == 201
    for skill in roadmap.json()["skills"]:
        started = await client.post(
            f"/api/v1/testing/roadmap/{roadmap.json()['id']}/skills/{skill['code']}/start",
            headers=candidate,
        )
        assert started.status_code == 201
        answers = [
            {"question_id": q["id"], "selected_answers": [correct[q["code"]]]}
            for q in started.json()["questions"]
        ]
        passed = await client.post(
            f"/api/v1/testing/{started.json()['session_id']}/submit",
            headers=candidate, json={"answers": answers},
        )
        assert passed.status_code == 200
    assert passed.json()["verified_grade"] == "junior"

    retake = await client.post("/api/v1/testing/start", headers=candidate, json={})
    assert retake.status_code == 201
    failed = await client.post(
        f"/api/v1/testing/{retake.json()['session_id']}/submit",
        headers=candidate, json={"answers": []},
    )
    assert failed.status_code == 200
    assert failed.json()["passed"] is False
    assert failed.json()["verified_grade"] == "junior"
    profile = await client.get("/api/v1/candidate/profile", headers=candidate)
    assert profile.json()["declared_grade"] == "junior"
    assert profile.json()["verified_grade"] == "junior"
    history = await client.get("/api/v1/testing/history", headers=candidate)
    assert history.status_code == 200
    assert len(history.json()) == 6
