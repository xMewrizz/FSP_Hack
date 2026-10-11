import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_candidate_registration_and_verification(client: AsyncClient):
    # 1. Регистрация кандидата
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "Password123!",
            "role": "candidate",
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    code = data["verification_code"]
    assert code is not None

    # 2. Подтверждение email по коду
    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "candidate@example.com",
            "code": code,
        },
    )
    assert ver_resp.status_code == 200
    tokens = ver_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["role"] == "candidate"
    assert tokens["is_verified"] is True
    assert tokens["onboarding_completed"] is False

    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Проверка GET /auth/me
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "candidate@example.com"
    assert me_data["role"] == "candidate"

    # 4. Онбординг кандидата (152-ФЗ, OSINT, грейд, город, FSP-77-001)
    onboard_resp = await client.post(
        "/api/v1/candidate/onboarding",
        headers=headers,
        json={
            "agreed_152_fz": True,
            "agreed_osint": True,
            "specialization": "Backend",
            "declared_grade": "senior",
            "work_format": "remote",
            "city": "Москва",
            "fsp_id": "FSP-77-001",
            "agreed_fsp_id_link": True,
            "first_name": "Иван",
            "last_name": "Иванов",
            "telegram": "@ivan_dev",
            "phone": "+79991234567",
        },
    )
    assert onboard_resp.status_code == 200
    candidate_profile = onboard_resp.json()
    assert candidate_profile["first_name"] == "Иван"
    assert candidate_profile["onboarding_completed"] is True
    assert candidate_profile["fsp_verified"] is True
    assert candidate_profile["fsp_id"] == "FSP-77-001"
    assert len(candidate_profile["achievements"]) >= 3

    # 5. Получение профиля кандидата
    prof_resp = await client.get("/api/v1/candidate/profile", headers=headers)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["fsp_verified"] is True
    assert prof_resp.json()["verified_grade"] is None

    linked = await client.post(
        "/api/v1/candidate/link-fsp", headers=headers,
        json={"fsp_id": "FSP-78-042"},
    )
    assert linked.status_code == 200
    assert linked.json()["fsp_id"] == "FSP-78-042"
    assert len(linked.json()["achievements"]) == 2
    assert all(not item["verified"] for item in linked.json()["achievements"])
    assert linked.json()["verified_grade"] is None


@pytest.mark.asyncio
async def test_osint_consent_from_registration_survives_onboarding_and_can_be_revoked(client: AsyncClient):
    registered = await client.post("/api/v1/auth/register", json={
        "email": "consent@example.com", "password": "Password123!",
        "role": "candidate", "agreed_osint": True,
    })
    assert registered.status_code == 201
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": "consent@example.com", "code": registered.json()["verification_code"],
    })
    assert verified.status_code == 200
    headers = {"Authorization": "Bearer " + verified.json()["access_token"]}
    onboarding = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "agreed_152_fz": True, "specialization": "Backend",
        "declared_grade": "junior", "work_format": "remote", "city": "Москва",
        "first_name": "Иван", "last_name": "Иванов",
    })
    assert onboarding.status_code == 200
    assert onboarding.json()["agreed_osint"] is True
    assert onboarding.json()["email_verified"] is True
    revoked = await client.put("/api/v1/candidate/profile", headers=headers, json={"agreed_osint": False})
    assert revoked.status_code == 200
    assert revoked.json()["agreed_osint"] is False


@pytest.mark.asyncio
async def test_candidate_onboarding_rejects_obvious_name_keysmashes(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "name-check@example.com", "password": "Password123!", "role": "candidate"},
    )
    assert reg_resp.status_code == 201
    verification = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "name-check@example.com", "code": reg_resp.json()["verification_code"]},
    )
    headers = {"Authorization": "Bearer " + verification.json()["access_token"]}

    response = await client.post(
        "/api/v1/candidate/onboarding",
        headers=headers,
        json={
            "agreed_152_fz": True,
            "specialization": "Backend",
            "declared_grade": "middle",
            "city": "Москва",
            "first_name": "asdfgh",
            "last_name": "Иванов",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_candidate_can_attach_and_remove_olympiad_pdf(client: AsyncClient):
    registered = await client.post("/api/v1/auth/register", json={
        "email": "diploma@example.com", "password": "Password123!", "role": "candidate",
    })
    assert registered.status_code == 201
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": "diploma@example.com", "code": registered.json()["verification_code"],
    })
    assert verified.status_code == 200
    headers = {"Authorization": "Bearer " + verified.json()["access_token"]}
    onboarding = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "agreed_152_fz": True,
        "specialization": "Backend",
        "declared_grade": "junior",
        "work_format": "remote",
        "city": "Moscow",
        "first_name": "Ivan",
        "last_name": "Ivanov",
    })
    assert onboarding.status_code == 200

    uploaded = await client.post(
        "/api/v1/candidate/olympiad-diplomas",
        headers=headers,
        files={"file": ("diploma.pdf", b"%PDF-1.4\nsample diploma", "application/pdf")},
    )
    assert uploaded.status_code == 201
    diploma = uploaded.json()
    assert diploma["file_name"] == "diploma.pdf"

    listed = await client.get("/api/v1/candidate/olympiad-diplomas", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [diploma]

    removed = await client.delete(f"/api/v1/candidate/olympiad-diplomas/{diploma['id']}", headers=headers)
    assert removed.status_code == 204
    listed_again = await client.get("/api/v1/candidate/olympiad-diplomas", headers=headers)
    assert listed_again.status_code == 200
    assert listed_again.json() == []


@pytest.mark.asyncio
async def test_employer_flow(client: AsyncClient):
    # 1. Регистрация работодателя
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "hr@techcorp.ru",
            "password": "Password123!",
            "role": "employer",
        },
    )
    assert reg_resp.status_code == 201
    code = reg_resp.json()["verification_code"]

    # 2. Подтверждение email
    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "hr@techcorp.ru", "code": code},
    )
    assert ver_resp.status_code == 200
    access_token = ver_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Онбординг компании
    onb_resp = await client.post(
        "/api/v1/employer/onboarding",
        headers=headers,
        json={
            "company_name": "Tech Corp AI",
            "description": "Разработка передовых ИТ-продуктов",
            "industry": "FinTech",
            "website": "https://techcorp.ru",
            "contact_person": "Анна Сидорова",
            "phone": "+79998887766",
            "city": "Санкт-Петербург",
        },
    )
    assert onb_resp.status_code == 200
    assert onb_resp.json()["company_name"] == "Tech Corp AI"
    assert onb_resp.json()["onboarding_completed"] is True

    # 4. Получение профиля работодателя
    emp_prof = await client.get("/api/v1/employer/profile", headers=headers)
    assert emp_prof.status_code == 200
    assert emp_prof.json()["contact_person"] == "Анна Сидорова"


@pytest.mark.asyncio
async def test_fsp_mock_endpoints(client: AsyncClient):
    # 1. Список спортсменов
    athletes_resp = await client.get("/api/v1/fsp/athletes")
    assert athletes_resp.status_code == 200
    athletes = athletes_resp.json()
    assert len(athletes) >= 4

    # 2. Верификация конкретного FSP ID
    verify_resp = await client.get("/api/v1/fsp/verify/FSP-78-042")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["found"] is True
    assert v_data["athlete_name"] == "Екатерина Кузнецова"

    # 3. Кейс отсутствия в ФСП (по ТЗ должно быть штатным ответом without error)
    not_found_resp = await client.get("/api/v1/fsp/verify/NON-EXISTENT-ID")
    assert not_found_resp.status_code == 200
    assert not_found_resp.json()["found"] is False

    # ФСП ID из публичного демо-списка не может служить для входа.
    userinfo_resp = await client.get("/api/v1/fsp/keycloak/userinfo?fsp_id=FSP-77-001")
    assert userinfo_resp.status_code == 404

    quick_login = await client.post("/api/v1/fsp/login-by-fsp-id?fsp_id=FSP-77-001")
    assert quick_login.status_code == 404
    assert "тестовая запись" in v_data["message"].lower()
    assert all(not item["verified"] for item in v_data["achievements"])


@pytest.mark.asyncio
async def test_token_refresh_and_logout(client: AsyncClient):
    # Регистрация и логин
    await client.post(
        "/api/v1/auth/register",
        json={"email": "session@test.com", "password": "SecretPassword1!", "role": "candidate"},
    )
    reg_data = (await client.post(
        "/api/v1/auth/register",
        json={"email": "session2@test.com", "password": "SecretPassword1!", "role": "candidate"},
    )).json()
    code = reg_data["verification_code"]

    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "session2@test.com", "code": code},
    )
    tokens = ver_resp.json()
    refresh_token = tokens["refresh_token"]

    # Обновление токенов
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 200

    # Попытка повторно использовать отозванный токен должна завершиться 401
    fail_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert fail_refresh.status_code == 401
