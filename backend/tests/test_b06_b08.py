import io
import pytest
from httpx import AsyncClient
from pypdf import PdfReader, PdfWriter

from app.services.pdf_service import EMPTY_RESUME_TEXT


@pytest.mark.asyncio
async def test_b08_demo_achievements_do_not_grant_grade(client: AsyncClient):
    """Привязка демо ID не подтверждает профессиональный грейд."""
    # Демо ID привязывается к уже зарегистрированному кандидату.
    reg = await client.post("/api/v1/auth/register", json={
        "email": "fsp-demo-test@example.com", "password": "Password123!", "role": "candidate",
    })
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": "fsp-demo-test@example.com", "code": reg.json()["verification_code"],
    })
    token = verified.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    onboard = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "first_name": "Тест", "last_name": "Кандидат", "specialization": "Backend",
        "declared_grade": "senior", "city": "Москва", "agreed_152_fz": True,
    })
    assert onboard.status_code == 200
    denied_onboarding = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "first_name": "Тест", "last_name": "Кандидат", "specialization": "Backend",
        "declared_grade": "senior", "city": "Москва", "agreed_152_fz": True,
        "fsp_id": "FSP-77-001",
    })
    assert denied_onboarding.status_code == 400
    denied = await client.post("/api/v1/candidate/link-fsp", headers=headers, json={"fsp_id": "FSP-77-001"})
    assert denied.status_code == 403
    denied_profile_update = await client.put(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"fsp_id": "FSP-77-001"},
    )
    assert denied_profile_update.status_code == 403
    consent = await client.put("/api/v1/candidate/profile", headers=headers, json={"agreed_fsp_id_link": True})
    assert consent.status_code == 200
    linked = await client.post("/api/v1/candidate/link-fsp", headers=headers, json={"fsp_id": "FSP-77-001"})
    assert linked.status_code == 200

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
        assert ach["verified"] is False

    withdrawn = await client.put(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"agreed_fsp_id_link": False},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["fsp_id"] is None
    assert withdrawn.json()["achievements"] == []

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
            "agreed_fsp_id_link": True,
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
            "agreed_osint": True,
        },
    )
    assert onb_resp.status_code == 200
    candidate_id = onb_resp.json()["id"]

    # Контакты не входят в опубликованный PDF.
    pdf_resp = await client.get("/api/v1/candidates/profile/pdf", headers=cand_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf_resp.content))
    extracted_text = reader.pages[0].extract_text()

    # Проверка кириллицы: читается имя и специализация, нет квадратов
    assert "Султан" in extracted_text
    assert "Багиров" in extracted_text
    assert "Backend" in extracted_text
    assert "sultan_dev" not in extracted_text
    assert "+7 999 111-22-33" not in extracted_text
    assert "заявленный" in extracted_text

    # Работодатель скачивает опубликованный PDF без контактов.
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
    assert "+7 999 111-22-33" not in emp_extracted_text
    revoked = await client.put("/api/v1/candidate/profile", headers=cand_headers,
                               json={"agreed_publication": False})
    assert revoked.status_code == 200
    assert (await client.get(f"/api/v1/candidates/{candidate_id}/pdf", headers=emp_headers)).status_code == 404
    assert (await client.get("/api/v1/candidates/profile/pdf", headers=cand_headers)).status_code == 403


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
            "agreed_publication": True,
            "agreed_osint": True,
        },
    )

    # 1. Скачиваем собственный PDF как тестовый документ с текстом
    pdf_resp = await client.get("/api/v1/candidates/profile/pdf", headers=cand_headers)
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
    unchanged = await client.get("/api/v1/candidate/profile", headers=cand_headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["skills"] == []

    before_score = unchanged.json()["profile_completeness"]["score"]
    attached = await client.post(
        "/api/v1/candidates/resume/attach",
        headers=cand_headers,
        files={"file": ("my_resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert attached.status_code == 200
    saved = await client.get("/api/v1/candidate/profile", headers=cand_headers)
    assert saved.json()["profile_completeness"]["score"] == before_score + 10
    assert saved.json()["resume_url"].endswith(".pdf")
    own_file = await client.get("/api/v1/candidate/resume/file", headers=cand_headers)
    assert own_file.status_code == 200
    assert own_file.content == pdf_bytes
    deleted = await client.delete("/api/v1/candidate/resume/versions", headers=cand_headers)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/candidate/resume/file", headers=cand_headers)).status_code == 404
    assert (await client.get("/api/v1/candidate/profile", headers=cand_headers)).json()["profile_completeness"]["score"] == before_score


@pytest.mark.asyncio
async def test_resume_can_be_attached_before_onboarding_finishes(client: AsyncClient):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas

    registered = await client.post("/api/v1/auth/register", json={
        "email": "resume.onboarding@fsp.ru", "password": "Password123!", "role": "candidate",
    })
    verified = await client.post("/api/v1/auth/verify-email", json={
        "email": "resume.onboarding@fsp.ru", "code": registered.json()["verification_code"],
    })
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    document = BytesIO()
    canvas = Canvas(document)
    canvas.drawString(60, 750, "Python Backend developer with SQL experience")
    canvas.save()
    pdf = document.getvalue()

    attached = await client.post("/api/v1/candidate/resume/attach", headers=headers,
                                 files={"file": ("resume.pdf", pdf, "application/pdf")})
    assert attached.status_code == 200, attached.text
    completed = await client.post("/api/v1/candidate/onboarding", headers=headers, json={
        "first_name": "Иван", "last_name": "Иванов", "city": "Москва",
        "specialization": "Backend", "declared_grade": "junior", "agreed_152_fz": True,
    })
    assert completed.status_code == 200, completed.text
    assert completed.json()["resume_url"]
    assert completed.json()["profile_completeness"]["score"] >= 10
    assert (await client.get("/api/v1/candidate/resume/file", headers=headers)).content == pdf
    employer_registered = await client.post("/api/v1/auth/register", json={
        "email": "resume.hr@fsp.ru", "password": "Password123!", "role": "employer",
    })
    employer_verified = await client.post("/api/v1/auth/verify-email", json={
        "email": "resume.hr@fsp.ru", "code": employer_registered.json()["verification_code"],
    })
    employer_headers = {"Authorization": f"Bearer {employer_verified.json()['access_token']}"}
    blocked = await client.get(f"/api/v1/candidate/{completed.json()['id']}/resume/file", headers=employer_headers)
    assert blocked.status_code == 404
    await client.delete("/api/v1/candidate/resume/versions", headers=headers)


@pytest.mark.asyncio
async def test_b22_pdf_without_text_does_not_change_profile(client: AsyncClient):
    """Скан без текстового слоя не считается распознанным резюме и не пишет навыки."""
    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "scan.resume@fsp.ru", "password": "Password123!", "role": "candidate"},
    )
    code = cand_reg.json()["verification_code"]
    cand_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "scan.resume@fsp.ru", "code": code},
    )
    cand_headers = {"Authorization": f"Bearer {cand_ver.json()['access_token']}"}
    await client.post(
        "/api/v1/candidates/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Скан",
            "last_name": "Пустой",
            "city": "Казань",
            "specialization": "Backend",
            "declared_grade": "junior",
            "agreed_152_fz": True,
        },
    )

    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)

    upload_resp = await client.post(
        "/api/v1/candidates/resume/upload",
        headers=cand_headers,
        files={"file": ("scan.pdf", buffer.getvalue(), "application/pdf")},
    )
    assert upload_resp.status_code == 400
    assert upload_resp.json()["detail"] == EMPTY_RESUME_TEXT
    profile = await client.get("/api/v1/candidate/profile", headers=cand_headers)
    assert profile.status_code == 200
    assert profile.json()["skills"] == []
    assert profile.json()["first_name"] == "Скан"
