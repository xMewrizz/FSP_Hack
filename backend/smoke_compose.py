"""Проверка основного сценария на запущенном backend с PostgreSQL.

Запуск: uv run python smoke_compose.py
Для другого порта задайте FSP_API_BASE_URL перед запуском.
Скрипт создаёт две новые тестовые учётные записи при каждом запуске.
"""

import os
import uuid

import httpx

from app.core.question_bank import PREDEFINED_QUESTIONS


def check(response: httpx.Response, expected: int) -> dict:
    if response.status_code != expected:
        raise AssertionError(
            f"{response.request.method} {response.request.url}: "
            f"ожидали {expected}, получили {response.status_code}: {response.text}"
        )
    return response.json()


def register(client: httpx.Client, email: str, role: str) -> dict[str, str]:
    created = check(
        client.post(
            "/auth/register",
            json={"email": email, "password": "SmokeTest123!", "role": role},
        ),
        201,
    )
    verified = check(
        client.post(
            "/auth/verify-email",
            json={"email": email, "code": created["verification_code"]},
        ),
        200,
    )
    return {"Authorization": f"Bearer {verified['access_token']}"}


def main() -> None:
    base_url = os.environ.get("FSP_API_BASE_URL", "http://localhost:8000/api/v1")
    suffix = uuid.uuid4().hex[:10]
    candidate_email = f"smoke-candidate-{suffix}@example.com"
    employer_email = f"smoke-employer-{suffix}@example.com"

    with httpx.Client(base_url=base_url, timeout=30) as client:
        check(client.get("/health"), 200)
        candidate_headers = register(client, candidate_email, "candidate")
        candidate = check(
            client.post(
                "/candidates/onboarding",
                headers=candidate_headers,
                json={
                    "first_name": "Тест",
                    "last_name": "Проверка",
                    "city": "Москва",
                    "specialization": "Backend",
                    "declared_grade": "junior",
                    "work_format": "remote",
                    "agreed_152_fz": True,
                    "agreed_osint": False,
                },
            ),
            200,
        )
        session = check(
            client.post(
                "/testing/start",
                headers=candidate_headers,
                json={"specialization": "Backend", "target_grade": "junior"},
            ),
            201,
        )
        keys = {question["code"]: question["correct_answers"] for question in PREDEFINED_QUESTIONS}
        answers = [
            {"question_id": question["id"], "selected_answers": keys[question["code"]]}
            for question in session["questions"]
        ]
        result = check(
            client.post(
                f"/testing/{session['session_id']}/submit",
                headers=candidate_headers,
                json={"answers": answers},
            ),
            200,
        )
        assert result["passed"] and result["verified_grade"] == "junior"

        employer_headers = register(client, employer_email, "employer")
        check(
            client.post(
                "/employers/onboarding",
                headers=employer_headers,
                json={"company_name": "Проверка B-00", "contact_person": "Тест"},
            ),
            200,
        )
        need = check(
            client.post(
                "/needs",
                headers=employer_headers,
                json={
                    "title": "Backend Junior",
                    "specialization": "Backend",
                    "required_grade": "junior",
                    "salary_min": 100000,
                    "salary_max": 150000,
                },
            ),
            201,
        )
        matches = check(
            client.get(f"/matching/for-need/{need['id']}", headers=employer_headers),
            200,
        )
        assert any(item["candidate_id"] == candidate["id"] for item in matches["candidates"])
        invitation = check(
            client.post(
                "/invitations",
                headers=employer_headers,
                json={
                    "candidate_id": candidate["id"],
                    "need_id": need["id"],
                    "offer_description": "Тестовое приглашение для проверки запуска",
                    "contact_method": "email",
                    "salary_min": 110000,
                    "salary_max": 140000,
                },
            ),
            201,
        )
        assert invitation["candidate_contacts"] is None
        accepted = check(
            client.post(
                f"/invitations/{invitation['id']}/accept",
                headers=candidate_headers,
                json={"reply": "Тестовый ответ"},
            ),
            200,
        )
        assert accepted["status"] == "accepted"
        sent = check(client.get("/invitations/sent", headers=employer_headers), 200)
        accepted_invitation = next(item for item in sent if item["id"] == invitation["id"])
        assert accepted_invitation["candidate_contacts"]["email"] == candidate_email

    print("B-00 live smoke: registration, test, matching, invitation, acceptance: OK")


if __name__ == "__main__":
    main()
