"""Saved resume versions belong only to the candidate who confirmed them."""

import pytest
from httpx import AsyncClient

from app.services.resume_versions import changed_roles, changed_work_lines, work_history_lines


async def candidate_headers(client: AsyncClient, email: str) -> dict[str, str]:
    registered = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "role": "candidate",
    })
    assert registered.status_code == 201
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": email, "code": registered.json()["verification_code"],
    })
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "agreed_152_fz": True, "specialization": "Backend", "declared_grade": "junior",
        "work_format": "remote", "city": "Москва", "first_name": "Тест", "last_name": "Кандидат",
    })
    assert onboarded.status_code == 200
    return headers


def test_comparison_only_marks_changed_work_lines():
    before = work_history_lines("Работа: Север 2020-2022\nPython\nРабота: Восток 2022-2024")
    after = work_history_lines("Работа: Север 2021-2022\nPython\nРабота: Восток 2022-2024")
    assert changed_work_lines(before, after) == {
        "added": ["Работа: Север 2021-2022"],
        "removed": ["Работа: Север 2020-2022"],
    }


def test_labeled_role_change_is_shown_without_guessing_unlabeled_jobs():
    before = "Компания: Север\nДолжность: разработчик\n2020-2022\n\nPython"
    after = "Компания: Север\nДолжность: тимлид\n2020-2022\n\nPython"
    assert changed_roles(before, after) == ["Север, 2020-2022: «разработчик» → «тимлид»"]
    assert changed_roles("Север, разработчик 2020-2022", "Север, тимлид 2020-2022") == []


@pytest.mark.asyncio
async def test_confirmed_resume_history_is_private_and_deletable(client: AsyncClient):
    owner = await candidate_headers(client, "resume-owner@example.com")
    stranger = await candidate_headers(client, "resume-stranger@example.com")
    first = "Backend разработчик\nКомпания Север, 2020-2022"
    second = "Backend разработчик\nКомпания Север, 2021-2022"

    for text in (first, first, second):
        saved = await client.put("/api/v1/candidate/profile", headers=owner, json={"resume_text": text})
        assert saved.status_code == 200, saved.text
        assert saved.json()["resume_text"] == text

    versions = (await client.get("/api/v1/candidate/resume/versions", headers=owner)).json()
    assert len(versions) == 2
    assert versions[0]["added"] == ["Компания Север, 2021-2022"]
    assert versions[0]["removed"] == ["Компания Север, 2020-2022"]
    assert versions[1]["added"] == []
    assert (await client.get("/api/v1/candidate/resume/versions", headers=stranger)).json() == []

    employer = await client.post("/api/v1/auth/register", json={
        "email": "resume-employer@example.com", "password": "Password123!", "role": "employer",
    })
    assert employer.status_code == 201
    verified_employer = await client.post("/api/v1/auth/verify-email", json={
        "email": "resume-employer@example.com", "code": employer.json()["verification_code"],
    })
    employer_headers = {"Authorization": f"Bearer {verified_employer.json()['access_token']}"}
    profile_id = (await client.get("/api/v1/candidate/profile", headers=owner)).json()["id"]
    url = f"/api/v1/candidate/{profile_id}/resume/versions"
    assert (await client.get(url, headers=employer_headers)).status_code == 404
    published = await client.put("/api/v1/candidate/profile", headers=owner, json={
        "agreed_publication": True, "visibility_public": True,
    })
    assert published.status_code == 200
    assert len((await client.get(url, headers=employer_headers)).json()) == 2
    assert (await client.get(url, headers=stranger)).status_code == 404

    deleted = await client.delete("/api/v1/candidate/resume/versions", headers=owner)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/candidate/resume/versions", headers=owner)).json() == []
    assert (await client.get("/api/v1/candidate/profile", headers=owner)).json()["resume_text"] is None
