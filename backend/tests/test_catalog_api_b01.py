import pytest
from httpx import AsyncClient


async def candidate_headers(client: AsyncClient) -> dict[str, str]:
    email = "catalog_candidate@example.com"
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "role": "candidate"},
    )
    assert registered.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    assert verified.status_code == 200
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Тест",
            "last_name": "Каталога",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "agreed_152_fz": True,
            "agreed_osint": False,
        },
    )
    assert onboarded.status_code == 200
    return headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("grade", "code_prefix"),
    [("junior", "BE-JR-"), ("middle", "BE-MID-"), ("senior", "BE-SR-")],
)
async def test_supported_pair_returns_only_its_questions(
    client: AsyncClient, grade: str, code_prefix: str
):
    headers = await candidate_headers(client)
    response = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "backend", "target_grade": grade},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["specialization"], body["target_grade"]) == ("Backend", grade)
    assert body["questions"]
    assert all(question["code"].startswith(code_prefix) for question in body["questions"])


@pytest.mark.asyncio
async def test_unsupported_pair_is_rejected_without_substitution(client: AsyncClient):
    headers = await candidate_headers(client)
    response = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Frontend", "target_grade": "middle"},
    )
    assert response.status_code == 400
    assert "Frontend" in response.json()["detail"]
    assert "не подставляются" in response.json()["detail"]
