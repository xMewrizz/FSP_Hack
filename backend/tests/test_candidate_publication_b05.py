import uuid
import pytest
from httpx import AsyncClient
from app.models.candidate import CandidateProfile
from conftest import TestingSessionLocal


async def register(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    created = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPassword123!", "role": role},
    )
    assert created.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": created.json()["verification_code"]},
    )
    assert verified.status_code == 200
    return {"Authorization": f"Bearer {verified.json()['access_token']}"}


@pytest.mark.asyncio
async def test_publication_requires_consent_and_can_be_revoked(client: AsyncClient):
    candidate_headers = await register(client, "private@example.com", "candidate")
    employer_headers = await register(client, "employer@example.com", "employer")

    invalid = await client.post(
        "/api/v1/candidate/onboarding",
        headers=candidate_headers,
        json={
            "first_name": "Тест",
            "last_name": "Кандидат",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "junior",
            "agreed_152_fz": True,
            "visibility_public": True,
        },
    )
    assert invalid.status_code == 400

    onboarded = await client.post(
        "/api/v1/candidate/onboarding",
        headers=candidate_headers,
        json={
            "first_name": "Тест",
            "last_name": "Кандидат",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "junior",
            "agreed_152_fz": True,
        },
    )
    assert onboarded.status_code == 200
    candidate = onboarded.json()
    assert not candidate["agreed_publication"]
    assert not candidate["visibility_public"]

    employer = await client.post(
        "/api/v1/employers/onboarding",
        headers=employer_headers,
        json={"company_name": "Тестовая компания", "contact_person": "HR"},
    )
    assert employer.status_code == 200
    need = await client.post(
        "/api/v1/needs",
        headers=employer_headers,
        json={
            "title": "Backend Junior",
            "specialization": "Backend",
            "required_grade": "junior",
            "salary_min": 100000,
            "salary_max": 150000,
        },
    )
    assert need.status_code == 201

    async def visible_ids() -> tuple[set[str], set[str]]:
        search = await client.get(
            "/api/v1/matching/search?specialization=Backend", headers=employer_headers
        )
        matching = await client.get(
            f"/api/v1/matching/for-need/{need.json()['id']}", headers=employer_headers
        )
        assert search.status_code == matching.status_code == 200
        return (
            {item["candidate_id"] for item in search.json()},
            {item["candidate_id"] for item in matching.json()["candidates"]},
        )

    assert all(candidate["id"] not in ids for ids in await visible_ids())
    invite_hidden = await client.post(
        "/api/v1/invitations",
        headers=employer_headers,
        json={
            "candidate_id": candidate["id"],
            "need_id": need.json()["id"],
            "offer_description": "Тестовое приглашение кандидату",
            "contact_method": "email",
            "salary_min": 110000,
            "salary_max": 140000,
        },
    )
    assert invite_hidden.status_code == 404

    without_consent = await client.put(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"visibility_public": True},
    )
    assert without_consent.status_code == 400
    published = await client.put(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"agreed_publication": True, "visibility_public": True},
    )
    assert published.status_code == 200
    assert published.json()["agreed_publication"] and published.json()["visibility_public"]
    # Согласие открывает профиль только после подтверждения категории тестом.
    assert all(candidate["id"] not in ids for ids in await visible_ids())
    async with TestingSessionLocal() as db:
        profile = await db.get(CandidateProfile, uuid.UUID(candidate["id"]))
        profile.verified_grade = "junior"
        profile.verified_specialization = "Backend"
        await db.commit()
    assert all(candidate["id"] in ids for ids in await visible_ids())

    hidden = await client.put(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"visibility_public": False},
    )
    assert hidden.status_code == 200
    assert hidden.json()["agreed_publication"] and not hidden.json()["visibility_public"]
    assert all(candidate["id"] not in ids for ids in await visible_ids())

    reopened = await client.put(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"visibility_public": True},
    )
    assert reopened.status_code == 200
    revoked = await client.put(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"agreed_publication": False},
    )
    assert revoked.status_code == 200
    assert not revoked.json()["agreed_publication"]
    assert not revoked.json()["visibility_public"]
    assert all(candidate["id"] not in ids for ids in await visible_ids())
