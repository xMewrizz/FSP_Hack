import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_b12_confident_score_upgrade_and_90day_cooldown(client: AsyncClient):
    """
    Test Task B-12:
    - Junior test passed with >=90% offers upgrade to Middle.
    - Status endpoint reflects cooldown active and middle unlocked as recommended.
    - Starting Senior directly without recommendation is blocked by 90-day cooldown.
    - Starting recommended Middle test is permitted despite cooldown.
    - Failing Middle test keeps Junior verified_grade intact (no auto-downgrade).
    """
    # 1. Register and onboard candidate
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "sultan_cand@fsp.ru", "password": "StrongPassword123!", "role": "candidate"},
    )
    assert reg_resp.status_code == 201
    verify_code = reg_resp.json()["verification_code"]

    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "sultan_cand@fsp.ru", "code": verify_code},
    )
    token = ver_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    onboard_resp = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Султан",
            "last_name": "Багиров",
            "city": "Москва",
            "phone": "+7 (999) 111-22-33",
            "telegram": "@sultan",
            "specialization": "Backend",
            "declared_grade": "junior",
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )
    assert onboard_resp.status_code == 200

    # 2. Check initial testing status
    status_resp = await client.get("/api/v1/testing/status", headers=headers)
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["verified_grade"] is None
    assert st_data["cooldown_active"] is False
    assert st_data["cooldown_days_remaining"] == 0
    assert any(g["grade"] == "junior" and g["is_available"] for g in st_data["available_grades"])

    # 3. Start Junior test
    start_resp = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Backend", "target_grade": "junior"},
    )
    assert start_resp.status_code == 201
    start_data = start_resp.json()
    session_id = start_data["session_id"]
    questions = start_data["questions"]
    assert len(questions) > 0

    # 4. Answer all correctly to get 100% (confident score >= 90%)
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
        headers=headers,
        json={"answers": answers},
    )
    assert submit_resp.status_code == 200
    res_data = submit_resp.json()
    assert res_data["passed"] is True
    assert res_data["verified_grade"] == "junior"
    assert res_data["percentage"] >= 90.0
    # Suggested higher test
    assert res_data["suggested_grade"] == "middle"

    # 5. Check testing status after confident pass
    status_resp2 = await client.get("/api/v1/testing/status", headers=headers)
    assert status_resp2.status_code == 200
    st2 = status_resp2.json()
    assert st2["verified_grade"] == "junior"
    assert st2["cooldown_active"] is True
    assert st2["cooldown_days_remaining"] == 90
    assert st2["suggested_grade"] == "middle"

    # Check available grades: junior available (current), middle available & recommended (upgrade), senior blocked
    grade_map = {g["grade"]: g for g in st2["available_grades"]}
    assert grade_map["junior"]["is_available"] is True
    assert grade_map["junior"]["is_current_verified"] is True
    assert grade_map["middle"]["is_available"] is True
    assert grade_map["middle"]["is_recommended"] is True
    assert grade_map["senior"]["is_available"] is False
    assert "90 дней" in grade_map["senior"]["reason"]

    # 6. Attempting Senior test directly is BLOCKED by 90-day cooldown
    senior_fail_resp = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Backend", "target_grade": "senior"},
    )
    assert senior_fail_resp.status_code == 400
    assert "90 дней" in senior_fail_resp.json()["detail"]

    # 7. Starting the recommended Middle upgrade test is PERMITTED
    middle_start_resp = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Backend", "target_grade": "middle"},
    )
    assert middle_start_resp.status_code == 201
    middle_session_id = middle_start_resp.json()["session_id"]
    middle_questions = middle_start_resp.json()["questions"]

    # 8. Submit intentionally wrong answers (fail Middle test)
    bad_answers = [{"question_id": q["id"], "selected_answers": ["Z"]} for q in middle_questions]
    middle_submit_resp = await client.post(
        f"/api/v1/testing/{middle_session_id}/submit",
        headers=headers,
        json={"answers": bad_answers},
    )
    assert middle_submit_resp.status_code == 200
    mid_res = middle_submit_resp.json()
    assert mid_res["passed"] is False
    assert mid_res["percentage"] == 0.0
    # Crucial TZ requirement: Verified grade does NOT downgrade!
    assert mid_res["verified_grade"] == "junior"
    # Suggests lower level (junior)
    assert mid_res["suggested_grade"] == "junior"

    # Verify candidate profile still has junior verified
    prof_resp = await client.get("/api/v1/candidates/profile", headers=headers)
    assert prof_resp.json()["verified_grade"] == "junior"


@pytest.mark.asyncio
async def test_b12_fail_suggests_lower_test_and_does_not_trigger_cooldown(client: AsyncClient):
    """
    Test Task B-12:
    - Candidate with declared Senior fails test.
    - Verified grade stays None (no auto-downgrade).
    - Lower test (Middle) is suggested.
    - Candidate can immediately take Middle test without cooldown block.
    """
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "unverified_senior@fsp.ru", "password": "StrongPassword123!", "role": "candidate"},
    )
    verify_code = reg_resp.json()["verification_code"]
    ver_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "unverified_senior@fsp.ru", "code": verify_code},
    )
    token = ver_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Иван",
            "last_name": "Тестов",
            "specialization": "Backend",
            "declared_grade": "senior",
            "agreed_152_fz": True,
            "agreed_osint": True,
        },
    )

    # 1. Start Senior test
    start_resp = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Backend", "target_grade": "senior"},
    )
    assert start_resp.status_code == 201
    s_id = start_resp.json()["session_id"]
    qs = start_resp.json()["questions"]

    # 2. Fail senior test
    bad_answers = [{"question_id": q["id"], "selected_answers": ["Z"]} for q in qs]
    sub_resp = await client.post(
        f"/api/v1/testing/{s_id}/submit",
        headers=headers,
        json={"answers": bad_answers},
    )
    assert sub_resp.status_code == 200
    res = sub_resp.json()
    assert res["passed"] is False
    assert res["verified_grade"] is None
    # Recommended lower grade
    assert res["suggested_grade"] == "middle"

    # 3. Status endpoint shows middle is recommended, no 90-day cooldown active
    st_resp = await client.get("/api/v1/testing/status", headers=headers)
    assert st_resp.status_code == 200
    st = st_resp.json()
    assert st["verified_grade"] is None
    assert st["cooldown_active"] is False
    assert st["suggested_grade"] == "middle"
    grade_map = {g["grade"]: g for g in st["available_grades"]}
    assert grade_map["middle"]["is_recommended"] is True

    # 4. Immediate attempt on suggested Middle test is allowed (no cooldown)
    mid_start_resp = await client.post(
        "/api/v1/testing/start",
        headers=headers,
        json={"specialization": "Backend", "target_grade": "middle"},
    )
    assert mid_start_resp.status_code == 201


