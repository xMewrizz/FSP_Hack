import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select

from app.models.candidate import CandidateProfile
from conftest import TestingSessionLocal


async def register_candidate(client: AsyncClient, email: str, first_name: str, grade: str):
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "candidate"},
    )
    assert registered.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    assert verified.status_code == 200
    profile = await client.post(
        "/api/v1/candidate/onboarding",
        headers={"Authorization": "Bearer" + " " + str(verified.json()["access_token"])},
        json={
            "first_name": first_name,
            "last_name": "Тестов",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": grade,
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
            "skills": ["Python", "PostgreSQL"],
        },
    )
    assert profile.status_code == 200
    return (
        {"Authorization": "Bearer" + " " + str(verified.json()["access_token"])},
        uuid.UUID(profile.json()["user_id"]),
    )


@pytest.mark.asyncio
async def test_candidate_can_request_opted_in_mentor_and_chat_after_acceptance(client: AsyncClient):
    candidate_headers, _ = await register_candidate(
        client, "mentee@example.com", "Иван", "junior"
    )
    mentor_headers, mentor_user_id = await register_candidate(
        client, "mentor@example.com", "Анна", "senior"
    )
    _, lower_mentor_user_id = await register_candidate(
        client, "lower-mentor@example.com", "Павел", "junior"
    )

    async with TestingSessionLocal() as db:
        mentor = await db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == mentor_user_id)
        )
        mentor.verified_grade = "senior"
        lower_mentor = await db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == lower_mentor_user_id)
        )
        lower_mentor.verified_grade = "junior"
        lower_mentor.mentor_available = True
        await db.commit()

    opt_in = await client.put(
        "/api/v1/candidate/profile",
        headers=mentor_headers,
        json={"mentor_available": True},
    )
    assert opt_in.status_code == 200
    assert opt_in.json()["mentor_available"] is True

    mentors = await client.get(
        "/api/v1/network/mentors?skill=python",
        headers=candidate_headers,
    )
    assert mentors.status_code == 200
    assert {item["user_id"] for item in mentors.json()} == {str(mentor_user_id), str(lower_mentor_user_id)}
    assert "email" not in mentors.json()[0]
    own_search = await client.get("/api/v1/network/mentors", headers=mentor_headers)
    assert all(item["user_id"] != str(mentor_user_id) for item in own_search.json())
    lower_request = await client.post(
        "/api/v1/network/mentorship-requests",
        headers=candidate_headers,
        json={
            "mentor_user_id": str(lower_mentor_user_id),
            "skill_focus": "Python",
            "message": "Запрос на наставничество",
        },
    )
    assert lower_request.status_code == 201

    request = await client.post(
        "/api/v1/network/mentorship-requests",
        headers=candidate_headers,
        json={
            "mentor_user_id": str(mentor_user_id),
            "skill_focus": "Python",
            "message": "Хочу подготовиться к уровню Senior по Python.",
        },
    )
    assert request.status_code == 201
    conversation_id = request.json()["id"]
    assert request.json()["status"] == "pending"
    assert request.json()["can_accept"] is False
    stats = await client.get("/api/v1/network/stats", headers=candidate_headers)
    assert stats.status_code == 200
    assert stats.json()["mentorship_requests_sent"] == 2

    assert (await client.post(
        f"/api/v1/network/conversations/{conversation_id}/messages",
        headers=candidate_headers,
        json={"body": "Ещё сообщение"},
    )).status_code == 409

    assert (await client.post(
        f"/api/v1/network/conversations/{conversation_id}/accept",
        headers=candidate_headers,
    )).status_code == 404
    accepted = await client.post(
        f"/api/v1/network/conversations/{conversation_id}/accept",
        headers=mentor_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    sent = await client.post(
        f"/api/v1/network/conversations/{conversation_id}/messages",
        headers=mentor_headers,
        json={"body": "Давайте разберём ваш план."},
    )
    assert sent.status_code == 201
    history = await client.get(
        f"/api/v1/network/conversations/{conversation_id}/messages",
        headers=candidate_headers,
    )
    assert [item["is_mine"] for item in history.json()["messages"]] == [True, False]

    outsider_headers, _ = await register_candidate(
        client, "outsider@example.com", "Олег", "middle"
    )
    assert (await client.get(
        f"/api/v1/network/conversations/{conversation_id}/messages",
        headers=outsider_headers,
    )).status_code == 404
