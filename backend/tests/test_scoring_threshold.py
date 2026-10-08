import pytest
from httpx import AsyncClient

from app.core.question_variants import BACKEND_FAMILIES, prepared_variants


@pytest.mark.asyncio
@pytest.mark.parametrize("grade, code_prefix", [("junior", "BE-JR-"), ("senior", "BE-SR-")])
async def test_first_bank_needs_nine_correct_answers_out_of_twelve(client: AsyncClient, grade: str, code_prefix: str):
    email = f"scoring-{grade}@example.com"
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "candidate"},
    )
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post(
        "/api/v1/candidate/onboarding", headers=headers,
        json={
            "first_name": "Иван", "last_name": "Иванов", "city": "Москва",
            "specialization": "Backend", "declared_grade": grade, "agreed_152_fz": True,
        },
    )
    assert onboarded.status_code == 200

    keys = {
        variant["code"]: variant["correct_answers"][0]
        for code in BACKEND_FAMILIES if code.startswith(code_prefix)
        for variant in prepared_variants(code)
    }
    for correct_answer_count in (8, 9):
        started = await client.post("/api/v1/testing/start", headers=headers, json={})
        assert started.status_code == 201
        questions = started.json()["questions"]
        assert len(questions) == 12
        before_submit = await client.get(
            f"/api/v1/testing/{started.json()['session_id']}", headers=headers,
        )
        assert before_submit.status_code == 200
        assert before_submit.json()["question_review"] == []
        answers = []
        for index, question in enumerate(questions):
            key = keys[question["code"]]
            selected = key if index < correct_answer_count else next(
                option["id"] for option in question["options"] if option["id"] != key
            )
            answers.append({"question_id": question["id"], "selected_answers": [selected]})
        submitted = await client.post(
            f"/api/v1/testing/{started.json()['session_id']}/submit",
            headers=headers, json={"answers": answers},
        )
        assert submitted.status_code == 200
        result = submitted.json()
        assert result["correct_count"] == correct_answer_count
        assert result["required_correct"] == 9
        assert result["passed"] is (correct_answer_count == 9)
        assert result["grade_confirmed"] is False
        assert sum(item["correct_count"] for item in result["skill_breakdown"]) == correct_answer_count
        assert result["verified_grade"] is None
        assert "не присваивает грейд" in result["feedback"]

    history = await client.get("/api/v1/testing/history", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["grade_confirmed"] is False
    if grade == "junior":
        senior_assessment = await client.post(
            "/api/v1/testing/start", headers=headers,
            json={"specialization": "Backend", "target_grade": "senior"},
        )
        assert senior_assessment.status_code == 201
