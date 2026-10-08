import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_platform_end_to_end_flow(client: AsyncClient):
    # ================= 1. Candidate Registration & Onboarding =================
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "candidate_test@fsp.ru", "password": "SecurePassword123!", "role": "candidate"},
    )
    assert reg_resp.status_code == 201
    code = reg_resp.json()["verification_code"]

    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "candidate_test@fsp.ru", "code": code},
    )
    assert ver_resp.status_code == 200
    cand_token = ver_resp.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # Onboarding
    onboard_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=cand_headers,
        json={
            "first_name": "Тест",
            "last_name": "Кандидатов",
            "phone": "+7 (999) 777-88-99",
            "telegram": "@test_candidate",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "junior",
            "work_format": "remote",
            "fsp_id": "FSP-77-001",
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
            "agreed_osint": True,
        },
    )
    assert onboard_resp.status_code == 200
    profile_data = onboard_resp.json()
    assert profile_data["fsp_verified"] is True
    assert profile_data["onboarding_completed"] is True
    assert len(profile_data["achievements"]) >= 1

    # ================= 2. PDF Profile Download =================
    pdf_resp = await client.get("/api/v1/candidates/profile/pdf", headers=cand_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 100

    # ================= 3. Testing & Grade Confirmation =================
    start_test_resp = await client.post(
        "/api/v1/testing/start",
        headers=cand_headers,
        json={"specialization": "Backend", "target_grade": "junior"},
    )
    assert start_test_resp.status_code == 201
    test_session = start_test_resp.json()
    session_id = test_session["session_id"]
    questions = test_session["questions"]
    assert len(questions) > 0

    # Answer all questions correctly
    answers = []
    for q in questions:
        if q["code"] == "BE-JR-01":
            answers.append({"question_id": q["id"], "selected_answers": ["D"]})
        elif q["code"] == "BE-JR-02":
            answers.append({"question_id": q["id"], "selected_answers": ["A"]})
        elif q["code"] == "BE-JR-03":
            answers.append({"question_id": q["id"], "selected_answers": ["B"]})
        elif q["code"] == "BE-JR-04":
            answers.append({"question_id": q["id"], "selected_answers": ["B"]})
        else:
            answers.append({"question_id": q["id"], "selected_answers": ["A"]})

    submit_resp = await client.post(
        f"/api/v1/testing/{session_id}/submit",
        headers=cand_headers,
        json={"answers": answers},
    )
    assert submit_resp.status_code == 200
    result = submit_resp.json()
    assert result["passed"] is True
    assert result["verified_grade"] == "junior"
    assert result["percentage"] >= 70.0
    assert len(result["skill_breakdown"]) > 0

    # Check candidate profile has updated verified_grade
    get_profile = await client.get("/api/v1/candidates/profile", headers=cand_headers)
    assert get_profile.status_code == 200
    assert get_profile.json()["verified_grade"] == "junior"

    # ================= 4. Employer Registration & Need Creation =================
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "employer_test@company.ru", "password": "SecurePassword123!", "role": "employer"},
    )
    assert emp_reg.status_code == 201
    emp_code = emp_reg.json()["verification_code"]

    emp_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "employer_test@company.ru", "code": emp_code},
    )
    emp_token = emp_ver.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Employer Onboarding
    emp_onboard = await client.post(
        "/api/v1/employers/onboarding",
        headers=emp_headers,
        json={
            "company_name": "ФСП Технологии",
            "description": "Передовая IT компания",
            "industry": "IT",
            "website": "https://fsp-tech.ru",
            "contact_person": "Алексей HR",
            "phone": "+7 (495) 123-45-67",
            "city": "Москва",
        },
    )
    assert emp_onboard.status_code == 200

    # Create Need (Invalid salary check)
    bad_salary = await client.post(
        "/api/v1/needs",
        headers=emp_headers,
        json={
            "title": "Junior Python Developer",
            "specialization": "Backend",
            "required_grade": "junior",
            "salary_min": 300000.0,
            "salary_max": 200000.0,  # invalid
        },
    )
    assert bad_salary.status_code == 422

    # Create Need (Valid)
    need_resp = await client.post(
        "/api/v1/needs",
        headers=emp_headers,
        json={
            "title": "Junior Python Developer",
            "specialization": "Backend",
            "required_grade": "junior",
            "required_skills": [
                {"name": "SQL & Транзакции", "weight": 1.0, "required": True},
                {"name": "Python & Структуры данных", "weight": 1.0, "required": True},
            ],
            "salary_min": 100000.0,
            "salary_max": 150000.0,
            "currency": "RUB",
            "work_format": "remote",
            "city": "Москва",
            "description": "Разработка микросервисов",
        },
    )
    assert need_resp.status_code == 201
    need_id = need_resp.json()["id"]

    # ================= 5. Matching & Candidate Search =================
    match_resp = await client.get(
        f"/api/v1/matching/for-need/{need_id}",
        headers=emp_headers,
    )
    assert match_resp.status_code == 200
    matched_data = match_resp.json()
    assert matched_data["total"] >= 1
    top_candidate = matched_data["candidates"][0]
    assert top_candidate["match_score"] > 50.0
    assert top_candidate["match_explanation"]["grade_match"] is True

    # Search candidates with filter
    search_resp = await client.get(
        "/api/v1/matching/search?specialization=Backend&grade=junior",
        headers=emp_headers,
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()) >= 1

    # ================= 6. Reverse Hiring Invitation Flow =================
    candidate_id = profile_data["id"]
    invite_resp = await client.post(
        "/api/v1/invitations",
        headers=emp_headers,
        json={
            "candidate_id": candidate_id,
            "need_id": need_id,
            "offer_description": "Приглашаем в команду бэкенда на разработку ядра платформы",
            "contact_method": "Telegram: @fsp_hr",
            "salary_min": 110000.0,
            "salary_max": 140000.0,
            "currency": "RUB",
        },
    )
    assert invite_resp.status_code == 201
    invitation = invite_resp.json()
    invitation_id = invitation["id"]
    assert invitation["status"] == "sent"
    # Contacts MUST be hidden before acceptance
    assert invitation["candidate_contacts"] is None

    # Candidate views invitations
    my_invites = await client.get("/api/v1/invitations/my", headers=cand_headers)
    assert my_invites.status_code == 200
    assert len(my_invites.json()) >= 1

    # Candidate accepts invitation
    accept_resp = await client.post(
        f"/api/v1/invitations/{invitation_id}/accept",
        headers=cand_headers,
        json={"reply": "С радостью принимаю приглашение!"},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    # Employer checks sent invitations -> contacts are now REVEALED
    sent_invites = await client.get("/api/v1/invitations/sent", headers=emp_headers)
    assert sent_invites.status_code == 200
    accepted_inv = [inv for inv in sent_invites.json() if inv["id"] == invitation_id][0]
    assert accepted_inv["status"] == "accepted"
    assert accepted_inv["candidate_contacts"] is not None
    assert accepted_inv["candidate_contacts"]["email"] == "candidate_test@fsp.ru"
    assert accepted_inv["candidate_contacts"]["telegram"] == "@test_candidate"

    # ================= 7. System Seed Data =================
    seed_resp = await client.post("/api/v1/system/seed")
    assert seed_resp.status_code == 201
    assert seed_resp.json()["candidates_seeded"] >= 4
