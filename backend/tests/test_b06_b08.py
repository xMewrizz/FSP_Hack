import io
import pytest
from httpx import AsyncClient
from pypdf import PdfReader


@pytest.mark.asyncio
async def test_b08_fsp_sso_and_achievements_do_not_grant_grade(client: AsyncClient):
    """
    B-08: Проверка входа по ФСП ID.
    Тестовые достижения явно обозначены и НЕ меняют/не подтверждают профессиональный грейд (ТЗ).
    """
    # 1. Логин по FSP ID через mock Keycloak
    login_resp = await client.post("/api/v1/fsp/login-by-fsp-id", params={"fsp_id": "FSP-77-001"})
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Проверяем профиль кандидата
    profile_resp = await client.get("/api/v1/candidate/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()

    assert profile["fsp_id"] == "FSP-77-001"
    assert profile["fsp_verified"] is True
    # Грейд НЕ подтверждён автоматически достижениями спорта!
    assert profile["verified_grade"] is None
    assert profile["declared_grade"] == "senior"

    # 3. Достижения содержат признак демо-данных и дисклеймер
    assert len(profile["achievements"]) >= 3
    for ach in profile["achievements"]:
        assert ach["is_demo"] is True
        assert "Демонстрационные данные" in ach["disclaimer"]

    # 4. Отвязка ФСП ID (DELETE /api/v1/candidate/link-fsp)
    unlink_resp = await client.delete("/api/v1/candidate/link-fsp", headers=headers)
    assert unlink_resp.status_code == 200
    unlinked_profile = unlink_resp.json()
    assert unlinked_profile["fsp_id"] is None
    assert unlinked_profile["fsp_verified"] is False
    assert len(unlinked_profile["achievements"]) == 0


@pytest.mark.asyncio
async def test_b06_standardized_pdf_profile_cyrillic_and_152fz_masking(client: AsyncClient):
    """
    B-06: Стандартизированный PDF-профиль.
    Проверка рендеринга кириллицы (без квадратов) и соблюдения 152-ФЗ при скачивании.
    """
    # 1. Регистрация и онбординг кандидата
    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "pdf.candidate@fsp.ru", "password": "Password123!", "role": "candidate"},
    )
    code = cand_reg.json()["verification_code"]
    cand_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "pdf.candidate@fsp.ru", "code": code},
    )
    cand_token = cand_ver.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    onb_resp = await client.post(
        "/api/v1/candidate/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Султан",
            "last_name": "Багиров",
            "phone": "+7 999 111-22-33",
            "telegram": "@sultan_dev",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "senior",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "bio": "Ведущий инженер бэкенд систем.",
            "fsp_id": "FSP-77-001",
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )
    assert onb_resp.status_code == 200
    candidate_id = onb_resp.json()["id"]

    # 2. Кандидат скачивает свой PDF с контактами
    pdf_resp = await client.get("/api/v1/candidates/profile/pdf?include_contacts=true", headers=cand_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf_resp.content))
    extracted_text = reader.pages[0].extract_text()

    # Проверка кириллицы: читается имя и специализация, нет квадратов
    assert "Султан" in extracted_text
    assert "Багиров" in extracted_text
    assert "Backend" in extracted_text
    assert "sultan_dev" in extracted_text
    assert "152-ФЗ" in extracted_text
    assert "ТЕСТ НЕ ПРОЙДЕН" in extracted_text  # грейд заявленный, тест еще не сдан

    # 3. Кандидат скачивает PDF без контактов
    pdf_resp_masked = await client.get("/api/v1/candidates/profile/pdf?include_contacts=false", headers=cand_headers)
    assert pdf_resp_masked.status_code == 200
    reader_masked = PdfReader(io.BytesIO(pdf_resp_masked.content))
    masked_text = reader_masked.pages[0].extract_text()
    assert "s***e@fsp.ru" in masked_text or "***" in masked_text
    assert "Скрыто" in masked_text

    # 4. Работодатель скачивает PDF кандидата по ID до приглашения
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "recruiter@corp.ru", "password": "Password123!", "role": "employer"},
    )
    emp_code = emp_reg.json()["verification_code"]
    emp_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "recruiter@corp.ru", "code": emp_code},
    )
    emp_token = emp_ver.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    await client.post(
        "/api/v1/employer/onboarding",
        headers=emp_headers,
        json={"company_name": "Corp IT", "contact_person": "HR Анна", "city": "Москва"},
    )

    emp_pdf_resp = await client.get(f"/api/v1/candidates/{candidate_id}/pdf", headers=emp_headers)
    assert emp_pdf_resp.status_code == 200
    emp_pdf_reader = PdfReader(io.BytesIO(emp_pdf_resp.content))
    emp_extracted_text = emp_pdf_reader.pages[0].extract_text()
    # Контакты должны быть скрыты от работодателя до принятия оффера (152-ФЗ)
    assert "Скрыто" in emp_extracted_text
    assert "+7 999 111-22-33" not in emp_extracted_text


@pytest.mark.asyncio
async def test_b22_resume_upload_and_parse(client: AsyncClient):
    """
    B-22: Загрузка PDF-резюме и извлечение данных для предзаполнения формы.
    """
    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "resume.user@fsp.ru", "password": "Password123!", "role": "candidate"},
    )
    code = cand_reg.json()["verification_code"]
    cand_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "resume.user@fsp.ru", "code": code},
    )
    cand_token = cand_ver.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    await client.post(
        "/api/v1/candidates/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Парсер",
            "last_name": "Резюмеев",
            "city": "Санкт-Петербург",
            "specialization": "Backend",
            "declared_grade": "middle",
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )

    # 1. Скачиваем собственный PDF как тестовый документ с текстом
    pdf_resp = await client.get("/api/v1/candidates/profile/pdf?include_contacts=true", headers=cand_headers)
    assert pdf_resp.status_code == 200
    pdf_bytes = pdf_resp.content

    # 2. Загружаем PDF в POST /api/v1/candidates/resume/upload
    upload_resp = await client.post(
        "/api/v1/candidates/resume/upload",
        headers=cand_headers,
        files={"file": ("my_resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    assert "text_preview" in data
    assert len(data["text_preview"]) > 0
    assert data["specialization"] == "Backend"

