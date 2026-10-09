import pytest
from httpx import AsyncClient


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
async def test_accepted_invitation_conversation_permissions_and_unread_count(client: AsyncClient):
    employer = await register_and_verify(client, "chat-employer@example.com", "employer")
    outsider = await register_and_verify(client, "chat-outsider@example.com", "employer")
    candidate = await register_and_verify(client, "chat-candidate@example.com", "candidate")

    await client.post(
        "/api/v1/employer/onboarding",
        headers=employer,
        json={"company_name": "Чат-компания", "contact_person": "Анна"},
    )
    candidate_profile = await client.post(
        "/api/v1/candidate/onboarding",
        headers=candidate,
        json={
            "first_name": "Иван",
            "last_name": "Чатов",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    invitation = await client.post(
        "/api/v1/invitations",
        headers=employer,
        json={
            "candidate_id": candidate_profile.json()["id"],
            "offer_description": "Предложение о работе",
            "contact_method": "Telegram",
            "salary_min": 200000,
            "salary_max": 250000,
        },
    )
    invitation_id = invitation.json()["id"]

    pending_chat = await client.get(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=candidate,
    )
    assert pending_chat.status_code == 404

    accepted = await client.post(
        f"/api/v1/invitations/{invitation_id}/accept",
        headers=candidate,
    )
    assert accepted.status_code == 200

    blank_message = await client.post(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=candidate,
        json={"body": "   "},
    )
    assert blank_message.status_code == 422

    sent = await client.post(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=candidate,
        json={"body": "Здравствуйте! Готов обсудить детали."},
    )
    assert sent.status_code == 201

    unread = await client.get("/api/v1/invitations/messages/unread-count", headers=employer)
    assert unread.json()["unread_count"] == 1
    assert (await client.get(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=outsider,
    )).status_code == 404

    employer_history = await client.get(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=employer,
    )
    assert employer_history.status_code == 200
    assert employer_history.json()["messages"][0]["is_mine"] is False
    assert employer_history.json()["messages"][0]["body"] == "Здравствуйте! Готов обсудить детали."
    assert employer_history.json()["unread_count"] == 0
    assert (await client.get(
        "/api/v1/invitations/messages/unread-count",
        headers=employer,
    )).json()["unread_count"] == 0

    reply = await client.post(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=employer,
        json={"body": "Добрый день! Предлагаю созвониться завтра."},
    )
    assert reply.status_code == 201
    candidate_history = await client.get(
        f"/api/v1/invitations/{invitation_id}/messages",
        headers=candidate,
    )
    assert [message["is_mine"] for message in candidate_history.json()["messages"]] == [True, False]
