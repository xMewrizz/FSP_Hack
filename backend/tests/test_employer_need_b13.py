import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.candidate import CandidateProfile
from conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_employer_need_salary_tax_type_and_weights_crud(client: AsyncClient):
    # 1. Register & verify employer
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "tax_test_emp@example.com", "password": "Password123!", "role": "employer"},
    )
    assert emp_reg.status_code == 201
    code = emp_reg.json()["verification_code"]
    ver_resp = await client.post("/api/v1/auth/verify-email", json={"email": "tax_test_emp@example.com", "code": code})
    assert ver_resp.status_code == 200
    emp_token = ver_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {emp_token}"}

    # Onboarding
    await client.post(
        "/api/v1/employer/onboarding",
        headers=headers,
        json={
            "company_name": "Tax Tech Solutions",
            "industry": "Fintech",
            "website": "https://taxtech.example.com",
            "contact_person": "HR Director",
            "phone": "+7 999 123-45-67",
            "city": "Москва",
        },
    )

    # 2. Test validation: salary_min > salary_max
    invalid_salary = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Invalid Salary Need",
            "specialization": "Backend",
            "required_grade": "senior",
            "salary_min": 350000.0,
            "salary_max": 200000.0,
            "salary_tax_type": "gross",
        },
    )
    assert invalid_salary.status_code == 422

    # 3. Test validation: invalid salary_tax_type
    invalid_tax = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Invalid Tax Need",
            "specialization": "Backend",
            "required_grade": "senior",
            "salary_min": 200000.0,
            "salary_max": 300000.0,
            "salary_tax_type": "without_tax",  # invalid
        },
    )
    assert invalid_tax.status_code == 422

    # 3a. Test validation: weight <= 0 rejected (422)
    bad_weight_zero = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Zero Weight Need",
            "specialization": "Backend",
            "required_grade": "middle",
            "required_skills": [{"name": "Python", "weight": 0.0}],
            "salary_min": 200000.0,
            "salary_max": 300000.0,
        },
    )
    assert bad_weight_zero.status_code == 422

    # 3b. Test validation: weight > 10 rejected (422)
    bad_weight_high = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "High Weight Need",
            "specialization": "Backend",
            "required_grade": "middle",
            "required_skills": [{"name": "Python", "weight": 15.0}],
            "salary_min": 200000.0,
            "salary_max": 300000.0,
        },
    )
    assert bad_weight_high.status_code == 422

    # 3c. Test validation: empty skill name rejected (422)
    bad_skill_name = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Empty Skill Need",
            "specialization": "Backend",
            "required_grade": "middle",
            "required_skills": [{"name": "   ", "weight": 3.0}],
            "salary_min": 200000.0,
            "salary_max": 300000.0,
        },
    )
    assert bad_skill_name.status_code == 422

    # 3d. Test Russian tax string normalization ("до вычета" -> "gross", "на руки" -> "net")
    ru_tax_need = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Russian Tax Need",
            "specialization": "Backend",
            "required_grade": "middle",
            "required_skills": [{"name": "Python", "weight": 3.0}],
            "salary_min": 150000.0,
            "salary_max": 200000.0,
            "salary_tax_type": "до вычета",
        },
    )
    assert ru_tax_need.status_code == 201
    assert ru_tax_need.json()["salary_tax_type"] == "gross"

    # 4. Create need with salary_tax_type="gross" and dynamic skill weights 1..5
    create_gross = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Senior Python Architect",
            "specialization": "Backend",
            "required_grade": "senior",
            "required_skills": [
                {"name": "Python", "weight": 5.0, "required": True},
                {"name": "PostgreSQL", "weight": 4.0, "required": True},
                {"name": "Docker", "weight": 2.0, "required": True},
            ],
            "salary_min": 250000.0,
            "salary_max": 350000.0,
            "salary_tax_type": "gross",
            "work_format": "remote",
            "city": "Москва",
            "description": "Проектирование ядра сервисов.",
        },
    )
    assert create_gross.status_code == 201
    gross_data = create_gross.json()
    assert gross_data["salary_tax_type"] == "gross"
    assert len(gross_data["required_skills"]) == 3
    assert gross_data["required_skills"][0]["name"] == "Python"
    assert gross_data["required_skills"][0]["weight"] == 5.0
    need_id = gross_data["id"]

    # 5. Create need with salary_tax_type="net" («на руки»)
    create_net = await client.post(
        "/api/v1/needs",
        headers=headers,
        json={
            "title": "Middle Backend Developer (Net Salary)",
            "specialization": "Backend",
            "required_grade": "middle",
            "required_skills": [
                {"name": "FastAPI", "weight": 5.0, "required": True},
                {"name": "Redis", "weight": 3.0, "required": True},
            ],
            "salary_min": 180000.0,
            "salary_max": 230000.0,
            "salary_tax_type": "net",
            "work_format": "office",
            "city": "Москва",
            "description": "Зарплата на руки.",
        },
    )
    assert create_net.status_code == 201
    net_data = create_net.json()
    assert net_data["salary_tax_type"] == "net"

    # 6. Retrieve need by ID
    get_need = await client.get(f"/api/v1/needs/{need_id}", headers=headers)
    assert get_need.status_code == 200
    assert get_need.json()["salary_tax_type"] == "gross"

    # 7. List my needs
    my_needs = await client.get("/api/v1/needs", headers=headers)
    assert my_needs.status_code == 200
    needs_list = my_needs.json()
    assert len(needs_list) >= 2
    assert any(n["salary_tax_type"] == "gross" for n in needs_list)
    assert any(n["salary_tax_type"] == "net" for n in needs_list)

    # 8. Update need salary_tax_type and skill weights
    update_resp = await client.put(
        f"/api/v1/needs/{need_id}",
        headers=headers,
        json={
            "salary_tax_type": "net",
            "required_skills": [
                {"name": "Python", "weight": 5.0, "required": True},
                {"name": "PostgreSQL", "weight": 5.0, "required": True},
                {"name": "Kubernetes", "weight": 3.0, "required": True},
            ],
        },
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["salary_tax_type"] == "net"
    assert len(updated_data["required_skills"]) == 3
    assert any(s["name"] == "Kubernetes" for s in updated_data["required_skills"])

    # 9. Test validation on update: new salary_min exceeding existing salary_max
    bad_salary_update = await client.put(
        f"/api/v1/needs/{need_id}",
        headers=headers,
        json={"salary_min": 999999.0},
    )
    assert bad_salary_update.status_code == 422


@pytest.mark.asyncio
async def test_matching_weighted_skills_and_salary_tax(client: AsyncClient):
    # Setup employer
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "matching_emp@example.com", "password": "Password123!", "role": "employer"},
    )
    code = emp_reg.json()["verification_code"]
    ver_resp = await client.post("/api/v1/auth/verify-email", json={"email": "matching_emp@example.com", "code": code})
    emp_token = ver_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    await client.post(
        "/api/v1/employer/onboarding",
        headers=emp_headers,
        json={
            "company_name": "MatchMaker Corp",
            "industry": "IT",
            "contact_person": "CTO",
            "city": "Москва",
        },
    )

    # Create need: Backend senior, salary up to 300 000 gross.
    # Python has weight 5.0, Docker has weight 1.0.
    need_resp = await client.post(
        "/api/v1/needs",
        headers=emp_headers,
        json={
            "title": "Senior Python Expert",
            "specialization": "Backend",
            "required_grade": "senior",
            "required_skills": [
                {"name": "Python", "weight": 5.0, "required": True},
                {"name": "Docker", "weight": 1.0, "required": True},
            ],
            "salary_min": 200000.0,
            "salary_max": 300000.0,
            "salary_tax_type": "gross",
            "work_format": "remote",
            "city": "Москва",
        },
    )
    assert need_resp.status_code == 201
    need_id = need_resp.json()["id"]

    # Helper to register candidates
    async def create_candidate(email: str, skills: list[str], salary: float | None, tax_type: str = "gross") -> str:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Password123!", "role": "candidate"},
        )
        c_code = reg.json()["verification_code"]
        c_ver = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": c_code})
        token = c_ver.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        onb = await client.post(
            "/api/v1/candidate/onboarding",
            headers=headers,
            json={
                "first_name": "Test",
                "last_name": email.split("@")[0].replace("_", "-"),
                "city": "Москва",
                "specialization": "Backend",
                "declared_grade": "senior",
                "work_format": "remote",
                "skills": skills,
                "salary_expectation": salary,
                "salary_tax_type": tax_type,
                "agreed_152_fz": True,
                "agreed_publication": True,
                "visibility_public": True,
            },
        )
        assert onb.status_code == 200
        return onb.json()["id"]

    # Cand A: has Python (weight 5.0), salary 250k gross (within budget & same tax)
    cand_a_id = await create_candidate("cand_a@example.com", ["Python"], 250000.0, "gross")

    # Cand B: has Docker only (weight 1.0), salary 250k gross (within budget & same tax)
    cand_b_id = await create_candidate("cand_b@example.com", ["Docker"], 250000.0, "gross")

    # Cand C: has Python (weight 5.0), but salary 350k gross (exceeds 300k max)
    cand_c_id = await create_candidate("cand_c@example.com", ["Python"], 350000.0, "gross")

    # Cand D: has Python (weight 5.0), salary 250k, but tax type is "net" (mismatch with need's "gross")
    cand_d_id = await create_candidate("cand_d@example.com", ["Python"], 250000.0, "net")

    # Cand E: has Python (weight 5.0), salary expectation is None
    cand_e_id = await create_candidate("cand_e@example.com", ["Python"], None, "gross")

    # Этот сценарий проверяет веса и зарплату. Допуск по грейду проверяется отдельно.
    async with TestingSessionLocal() as db:
        profiles = (await db.scalars(select(CandidateProfile))).all()
        for profile in profiles:
            if str(profile.id) in {cand_a_id, cand_b_id, cand_c_id, cand_d_id, cand_e_id}:
                profile.verified_grade = "senior"
                profile.verified_specialization = "Backend"
        await db.commit()

    # Query matching endpoint
    matching_resp = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=emp_headers)
    assert matching_resp.status_code == 200
    matched_data = matching_resp.json()
    candidates_by_id = {c["candidate_id"]: c for c in matched_data["candidates"]}

    item_a = candidates_by_id[cand_a_id]
    item_b = candidates_by_id[cand_b_id]
    item_c = candidates_by_id[cand_c_id]
    item_d = candidates_by_id[cand_d_id]
    item_e = candidates_by_id[cand_e_id]

    # Verify skill weighting effect:
    # Cand A (Python, weight 5/6 = 83.3%) must score higher than Cand B (Docker, weight 1/6 = 16.7%)
    assert item_a["match_score"] > item_b["match_score"]

    # Verify Cand A: salary_match is True, matching note
    assert item_a["match_explanation"]["salary_match"] is True
    assert "укладываются в бюджет" in item_a["match_explanation"]["salary_note"]
    assert "Зарплатные ожидания соответствуют" in item_a["match_explanation"]["summary"]

    # Verify Cand C: salary_match is False because 350k > 300k
    assert item_c["match_explanation"]["salary_match"] is False
    assert "выше максимума" in item_c["match_explanation"]["salary_note"]
    assert item_a["match_score"] > item_c["match_score"]

    # Verify Cand D: tax type mismatch ("net" vs "gross")
    assert item_d["match_explanation"]["salary_match"] is False
    assert "Разный налоговый базис" in item_d["match_explanation"]["salary_note"]
    assert "согласование налогового типа" in item_d["match_explanation"]["summary"]

    # Verify Cand E: salary expectation is None -> salary_match is None (neutral)
    assert item_e["match_explanation"]["salary_match"] is None
    assert "не указаны" in item_e["match_explanation"]["salary_note"]

    # Cand F: has compound skill "Python & Структуры данных" -> must match requirement "Python"
    cand_f_id = await create_candidate("cand_f@example.com", ["Python & Структуры данных"], 250000.0, "gross")
    async with TestingSessionLocal() as db:
        profile = await db.get(CandidateProfile, uuid.UUID(cand_f_id))
        profile.verified_grade = "senior"
        profile.verified_specialization = "Backend"
        await db.commit()
    resp_f = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=emp_headers)
    assert resp_f.status_code == 200
    item_f = next(c for c in resp_f.json()["candidates"] if c["candidate_id"] == cand_f_id)
    assert any("python" in s.lower() for s in item_f["match_explanation"]["matched_skills"])

    # Dynamic Need Tax Type Toggle:
    # Update need from "gross" to "net"
    toggle_resp = await client.put(
        f"/api/v1/needs/{need_id}",
        headers=emp_headers,
        json={"salary_tax_type": "net"},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["salary_tax_type"] == "net"

    # Re-fetch matching: now Cand D ("net") should MATCH, and Cand A ("gross") should MISMATCH
    re_matched = await client.get(f"/api/v1/matching/for-need/{need_id}", headers=emp_headers)
    assert re_matched.status_code == 200
    candidates_after_toggle = {c["candidate_id"]: c for c in re_matched.json()["candidates"]}

    item_d_after = candidates_after_toggle[cand_d_id]
    item_a_after = candidates_after_toggle[cand_a_id]

    assert item_d_after["match_explanation"]["salary_match"] is True
    assert "укладываются в бюджет" in item_d_after["match_explanation"]["salary_note"]

    assert item_a_after["match_explanation"]["salary_match"] is False
    assert "Разный налоговый базис" in item_a_after["match_explanation"]["salary_note"]


@pytest.mark.asyncio
async def test_candidate_profile_salary_and_tax_crud(client: AsyncClient):
    # Register candidate
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "salary_cand@example.com", "password": "Password123!", "role": "candidate"},
    )
    assert reg.status_code == 201
    code = reg.json()["verification_code"]
    ver = await client.post("/api/v1/auth/verify-email", json={"email": "salary_cand@example.com", "code": code})
    token = ver.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Onboarding with 180k net
    onb = await client.post(
        "/api/v1/candidate/onboarding",
        headers=headers,
        json={
            "first_name": "Зарплатный",
            "last_name": "Кандидат",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "salary_expectation": 180000.0,
            "salary_tax_type": "net",
            "skills": ["Python", "FastAPI"],
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert onb.status_code == 200
    onb_data = onb.json()
    assert onb_data["salary_expectation"] == 180000.0
    assert onb_data["salary_tax_type"] == "net"

    # Get profile
    prof_resp = await client.get("/api/v1/candidate/profile", headers=headers)
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["salary_expectation"] == 180000.0
    assert prof_data["salary_tax_type"] == "net"

    # Update profile to 250k gross using Russian string "до вычета"
    update_resp = await client.put(
        "/api/v1/candidate/profile",
        headers=headers,
        json={
            "salary_expectation": 250000.0,
            "salary_tax_type": "до вычета",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["salary_expectation"] == 250000.0
    assert updated["salary_tax_type"] == "gross"


@pytest.mark.asyncio
async def test_system_seed_populates_b13_data(client: AsyncClient):
    seed_resp = await client.post("/api/v1/system/seed")
    assert seed_resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "hr@yandex-team.ru", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check that search results include salary and tax fields
    search_resp = await client.get("/api/v1/matching/search", headers=headers)
    assert search_resp.status_code == 200
    candidates = search_resp.json()
    assert len(candidates) > 0
    # Alex Smirnov should have salary_expectation and gross tax type
    alex = next((c for c in candidates if c["first_name"] == "Алексей"), None)
    assert alex is not None
    assert alex["salary_expectation"] == 320000.0
    assert alex["salary_tax_type"] == "gross"

    ds_search = await client.get(
        "/api/v1/matching/search?specialization=Data%20Science%20%2F%20ML",
        headers=headers,
    )
    assert ds_search.status_code == 200
    ds_candidates = ds_search.json()
    assert len(ds_candidates) == 9
    assert sorted(candidate["verified_grade"] for candidate in ds_candidates) == [
        "junior", "junior", "junior", "middle", "middle", "middle", "senior", "senior", "senior",
    ]
    assert len({tuple(candidate["skills"]) for candidate in ds_candidates}) == 9
    assert (await client.post("/api/v1/system/seed")).status_code == 201
    repeated = await client.get(
        "/api/v1/matching/search?specialization=Data%20Science%20%2F%20ML", headers=headers,
    )
    assert len(repeated.json()) == 9
