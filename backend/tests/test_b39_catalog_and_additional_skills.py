import pytest
from httpx import AsyncClient

from app.core.question_variants import prepared_variants
from open_assessment_helpers import finish_open_assessment


async def register_and_onboard_candidate(
    client: AsyncClient, email: str, language: str = "Python", grade: str = "junior"
) -> dict[str, str]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "candidate"},
    )
    assert registered.status_code == 201, registered.text
    verification_code = registered.json()["verification_code"]

    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": verification_code},
    )
    assert verified.status_code == 200, verified.text
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}

    onboarded = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Каталог",
            "last_name": "Тестер",
            "city": "Москва",
            "specialization": "Backend",
            "programming_language": language,
            "declared_grade": grade,
            "agreed_152_fz": True,
        },
    )
    assert onboarded.status_code == 200, onboarded.text
    await client.put(
        "/api/v1/candidates/profile",
        headers=headers,
        json={"agreed_test_confidentiality": True},
    )
    return headers


async def finish_skill(client: AsyncClient, headers: dict[str, str], assessment_id: str, code: str, score: int):
    started = await client.post(
        f"/api/v1/testing/roadmap/{assessment_id}/skills/{code}/start",
        headers=headers,
    )
    assert started.status_code == 201, started.text
    questions = started.json()["questions"]
    answers = []
    for index, question in enumerate(questions):
        base_code = question["code"].split("-V")[0]
        variant = next(
            item for item in prepared_variants(base_code) if item["code"] == question["code"]
        )
        correct = variant["correct_answers"][0]
        selected = (
            correct
            if index < score
            else next(option["id"] for option in question["options"] if option["id"] != correct)
        )
        answers.append({"question_id": question["id"], "selected_answers": [selected]})

    submitted = await client.post(
        f"/api/v1/testing/{started.json()['session_id']}/submit",
        headers=headers,
        json={"answers": answers},
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


@pytest.mark.asyncio
async def test_b39_catalog_endpoint_structure(client: AsyncClient):
    """B-39: Каталог специализаций, языков и тестов."""
    resp = await client.get("/api/v1/testing/catalog")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "specializations" in data
    assert "supported_pairs" in data

    specs = {item["specialization"]: item for item in data["specializations"]}
    assert "Backend" in specs
    assert "Data Science / ML" in specs
    assert "Frontend" in specs

    # Backend доступен с Python, другие языки помечены как недоступные
    backend = specs["Backend"]
    assert backend["is_available"] is True
    assert backend["available_grades"] == ["junior", "middle", "senior"]
    assert any(lang["name"] == "Python" and lang["available"] is True for lang in backend["languages"])
    assert any(lang["name"] == "Go" and lang["available"] is False for lang in backend["languages"])

    # Data Science / ML доступен с Python
    ds = specs["Data Science / ML"]
    assert ds["is_available"] is True
    assert ds["available_grades"] == ["junior", "middle", "senior"]
    assert any(lang["name"] == "Python" and lang["available"] is True for lang in ds["languages"])

    # Обязательные и дополнительные навыки
    req_codes = [s["code"] for s in backend["required_skills"]]
    assert "backend_python" in req_codes
    assert "sql" in req_codes
    assert "api" in req_codes
    assert "reliability" in req_codes

    extra_codes = [s["code"] for s in backend["additional_skills"]]
    assert "git" in extra_codes

    # Frontend недоступен без готового банка
    frontend = specs["Frontend"]
    assert frontend["is_available"] is False


@pytest.mark.asyncio
async def test_b39_rejects_unsupported_language_on_onboarding_and_update(client: AsyncClient):
    """B-39: Неподготовленные языки нельзя указывать как доступные для Backend-теста."""
    # Регистрация
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "unsupported-lang@example.com", "password": "Password123!", "role": "candidate"},
    )
    code = reg.json()["verification_code"]
    auth = await client.post("/api/v1/auth/verify-email", json={"email": "unsupported-lang@example.com", "code": code})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    # Попытка онбординга с Go для Backend
    bad_onboard = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Иван",
            "last_name": "Гофер",
            "city": "Москва",
            "specialization": "Backend",
            "programming_language": "Go",
            "declared_grade": "junior",
            "agreed_152_fz": True,
        },
    )
    assert bad_onboard.status_code == 400
    assert "только базовый тест на Python" in bad_onboard.json()["detail"]

    # Успешный онбординг с Python
    ok_onboard = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Иван",
            "last_name": "Гофер",
            "city": "Москва",
            "specialization": "Backend",
            "programming_language": "Python",
            "declared_grade": "junior",
            "agreed_152_fz": True,
        },
    )
    assert ok_onboard.status_code == 200

    # Попытка смены языка на Java через update_profile
    bad_update = await client.put(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"programming_language": "Java"},
    )
    assert bad_update.status_code == 400
    assert "только базовый тест на Python" in bad_update.json()["detail"]


@pytest.mark.asyncio
async def test_b39_additional_skill_appears_in_profile_without_altering_grade(client: AsyncClient):
    """B-39: Результат дополнительного навыка отображается в профиле, но не меняет подтверждённый грейд."""
    headers = await register_and_onboard_candidate(client, "b39-additional@example.com")

    # Исходный профиль: additional_skills пуст
    prof_before = await client.get("/api/v1/candidates/profile", headers=headers)
    assert prof_before.status_code == 200
    assert prof_before.json()["additional_skills"] == []
    assert prof_before.json()["verified_grade"] is None

    # Проходим полный обязательный roadmap на Junior
    roadmap_resp = await client.post("/api/v1/testing/roadmap", headers=headers, json={})
    assert roadmap_resp.status_code == 201
    assessment_id = roadmap_resp.json()["id"]

    for code in ("backend_python", "sql", "api", "reliability"):
        await finish_skill(client, headers, assessment_id, code, 10)
    await finish_open_assessment(assessment_id)

    prof_junior = (await client.get("/api/v1/candidates/profile", headers=headers)).json()
    assert prof_junior["verified_grade"] == "junior"
    assert prof_junior["additional_skills"] == []

    # Сдаём дополнительный навык: Git Junior
    start_extra = await client.post(
        "/api/v1/testing/additional/git/start",
        headers=headers,
        json={"target_grade": "junior"},
    )
    assert start_extra.status_code == 201
    session_id = start_extra.json()["session_id"]
    questions = start_extra.json()["questions"]

    answers = []
    for q in questions:
        from app.core.additional_skill_bank import ADDITIONAL_SKILLS
        variant = next(item for item in ADDITIONAL_SKILLS["git"]["questions"] if item["code"] == q["code"])
        correct_text = next(item["text"] for item in variant["options"] if item["id"] in variant["correct_answers"])
        answers.append({"question_id": q["id"], "selected_answers": [next(item["id"] for item in q["options"] if item["text"] == correct_text)]})

    submit_extra = await client.post(
        f"/api/v1/testing/{session_id}/submit",
        headers=headers,
        json={"answers": answers},
    )
    assert submit_extra.status_code == 200
    assert submit_extra.json()["passed"] is True

    # Проверяем профиль кандидата:
    # 1. additional_skills содержит запись по Git
    # 2. verified_grade остался "junior" (не изменился!)
    prof_after = (await client.get("/api/v1/candidates/profile", headers=headers)).json()
    assert prof_after["verified_grade"] == "junior"
    assert len(prof_after["additional_skills"]) == 1

    git_res = prof_after["additional_skills"][0]
    assert git_res["code"] == "git"
    assert git_res["label"] == "Git"
    assert git_res["percentage"] == 100.0
    assert git_res["level_out_of_ten"] == 10.0
    assert git_res["target_grade"] == "all"
    assert git_res["completed_at"] is not None
