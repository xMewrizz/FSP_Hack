import pytest
from httpx import AsyncClient

from app.core.open_question_bank import (
    OPEN_QUESTIONS,
    get_open_question_by_code,
)
from app.services.open_question_service import get_public_open_questions


def test_open_questions_bank_structure():
    assert len(OPEN_QUESTIONS) == 16
    codes = [q["code"] for q in OPEN_QUESTIONS]
    assert len(codes) == len(set(codes))

    be_questions = [q for q in OPEN_QUESTIONS if q["specialization"] == "Backend"]
    ds_questions = [q for q in OPEN_QUESTIONS if q["specialization"] == "Data Science"]
    assert len(be_questions) == 8
    assert len(ds_questions) == 8

    # Проверка распределения по грейдам
    for spec_questions in (be_questions, ds_questions):
        juniors = [q for q in spec_questions if q["grade"] == "junior"]
        middles = [q for q in spec_questions if q["grade"] == "middle"]
        seniors = [q for q in spec_questions if q["grade"] == "senior"]
        assert len(juniors) == 2
        assert len(middles) == 4
        assert len(seniors) == 2

    # Проверка структуры каждого вопроса
    for q in OPEN_QUESTIONS:
        assert q["code"].startswith("OPEN-")
        assert q["specialization"] in ("Backend", "Data Science")
        assert q["grade"] in ("junior", "middle", "senior")
        assert q["question_type"] in ("free_text", "code")
        assert len(q["skill"]) > 3
        assert len(q["acceptable_solutions"]) >= 2
        assert len(q["rubric_criteria"]) >= 3
        assert len(q["reference_solution"]) > 20
        assert len(q["question_text"]) > 20

    public = get_public_open_questions()
    assert len(public) == 16
    for pub in public:
        assert "reference_solution" not in pub
        assert "rubric_criteria" in pub
        assert "code" in pub
        assert "skill" in pub
        assert "acceptable_solutions" in pub

    # Проверка фильтра по грейду
    juniors_pub = get_public_open_questions(grade="junior")
    assert len(juniors_pub) == 4
    seniors_pub = get_public_open_questions(grade="senior")
    assert len(seniors_pub) == 4
    ds_middles_pub = get_public_open_questions(specialization="Data Science", grade="middle")
    assert len(ds_middles_pub) == 4


@pytest.mark.asyncio
async def test_open_questions_endpoints_grade_filter(client: AsyncClient):
    resp = await client.get("/api/v1/testing/open-questions?grade=junior")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 4
    for it in items:
        assert it["grade"] == "junior"
        assert "skill" in it
        assert len(it["acceptable_solutions"]) > 0

    resp_sr = await client.get("/api/v1/testing/open-questions?specialization=Backend&grade=senior")
    assert resp_sr.status_code == 200
    items_sr = resp_sr.json()
    assert len(items_sr) == 2
    for it in items_sr:
        assert it["specialization"] == "Backend"
        assert it["grade"] == "senior"


async def open_test_candidate_headers(client: AsyncClient, email: str = "open_cand@example.com") -> dict[str, str]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "role": "candidate"},
    )
    assert registered.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    assert verified.status_code == 200
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboarded = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Иван",
            "last_name": "Открытый",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "agreed_152_fz": True,
            "agreed_osint": False,
        },
    )
    assert onboarded.status_code == 200
    return headers


@pytest.mark.asyncio
async def test_list_open_questions_api(client: AsyncClient):
    resp = await client.get("/api/v1/testing/open-questions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    for item in data:
        assert "reference_solution" not in item
        assert "code" in item
        assert "rubric_criteria" in item


@pytest.mark.asyncio
async def test_get_single_open_question_api(client: AsyncClient):
    resp = await client.get("/api/v1/testing/open-questions/OPEN-BE-ARCH-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "OPEN-BE-ARCH-01"
    assert data["question_type"] == "free_text"
    assert "reference_solution" not in data

    not_found = await client.get("/api/v1/testing/open-questions/OPEN-NON-EXISTENT")
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_submit_open_architecture_answer(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "arch_cand@example.com")
    answer = (
        "1. В базе данных создаем таблицу payments с уникальным idempotency_key (UNIQUE constraint) "
        "и статусами PENDING, PROCESSED, FAILED. "
        "2. При получении webhook открываем транзакцию с SELECT ... FOR UPDATE по ключу для защиты от race conditions. "
        "3. Если запись уже в статусе PROCESSED, завершаем транзакцию и возвращаем сохраненный кэшированный ответ HTTP 200 без повторного начисления. "
        "4. При сетевых сбоях и таймаутах статус остается PENDING для последующей асинхронной сверки воркером (reconciliation)."
    )
    resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-ARCH-01/submit",
        headers=headers,
        json={"answer_text": answer},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["question_code"] == "OPEN-BE-ARCH-01"
    assert body["score"] >= 0.70
    assert body["passed"] is True
    assert body["evaluator"] in ("llm_qwen3", "fallback_heuristic")
    assert body["needs_manual_review"] is True or body["evaluator"] == "llm_qwen3"
    assert len(body["criterion_scores"]) >= 3

    # Проверяем историю отправок
    hist_resp = await client.get("/api/v1/testing/open-submissions", headers=headers)
    assert hist_resp.status_code == 200
    submissions = hist_resp.json()
    assert len(submissions) >= 1
    assert submissions[0]["question_code"] == "OPEN-BE-ARCH-01"


@pytest.mark.asyncio
async def test_submit_open_code_answer_and_syntax_error(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "code_cand@example.com")

    # Валидный код
    valid_code = """from collections import deque

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.buckets = {}

    def allow_request(self, key: str, current_time: float) -> bool:
        if key not in self.buckets:
            self.buckets[key] = deque()
        q = self.buckets[key]
        threshold = current_time - self.window_seconds
        while q and q[0] <= threshold:
            q.popleft()
        if len(q) < self.max_requests:
            q.append(current_time)
            return True
        return False
"""
    resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-CODE-01/submit",
        headers=headers,
        json={"answer_text": valid_code},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["score"] >= 0.70
    assert body["passed"] is True

    # Синтаксическая ошибка
    broken_code = "def allow_request(key: str\n    broken syntax !!!"
    broken_resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-CODE-01/submit",
        headers=headers,
        json={"answer_text": broken_code},
    )
    assert broken_resp.status_code == 201
    broken_body = broken_resp.json()
    assert broken_body["score"] < 0.50
    assert broken_body["passed"] is False
    assert broken_body["needs_manual_review"] is True
    assert "Синтаксическая ошибка" in broken_body["feedback"]


@pytest.mark.asyncio
async def test_manual_reviewer_workflow(client: AsyncClient):
    import uuid

    # 1. Кандидат отправляет решение с синтаксической ошибкой (needs_manual_review = True)
    cand_headers = await open_test_candidate_headers(client, "cand_review_need@example.com")
    broken_code = "def allow_request(key: str\n    broken syntax !!!"
    sub_resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-CODE-01/submit",
        headers=cand_headers,
        json={"answer_text": broken_code},
    )
    assert sub_resp.status_code == 201
    submission = sub_resp.json()
    submission_id = submission["id"]
    assert submission["needs_manual_review"] is True

    # 2. Кандидат не имеет права вызывать reviewer endpoints (403 Forbidden)
    cand_pending_resp = await client.get(
        "/api/v1/testing/open-submissions/pending-review",
        headers=cand_headers,
    )
    assert cand_pending_resp.status_code == 403

    cand_review_attempt = await client.post(
        f"/api/v1/testing/open-submissions/{submission_id}/review",
        headers=cand_headers,
        json={"score": 1.0, "passed": True, "notes": "Self review attempt"},
    )
    assert cand_review_attempt.status_code == 403

    # 3. Регистрируем работодателя / эксперта
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "lead_ds_reviewer@corp.ru", "password": "Password123!", "role": "employer"},
    )
    emp_code = emp_reg.json()["verification_code"]
    emp_ver = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "lead_ds_reviewer@corp.ru", "code": emp_code},
    )
    emp_token = emp_ver.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    await client.post(
        "/api/v1/employer/onboarding",
        headers=emp_headers,
        json={"company_name": "Reviewer Team", "contact_person": "Lead Architect", "city": "Москва"},
    )

    # 4. Работодатель видит submission в очереди на ручную проверку
    pending_resp = await client.get(
        "/api/v1/testing/open-submissions/pending-review",
        headers=emp_headers,
    )
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    target_item = next((item for item in pending_list if item["id"] == submission_id), None)
    assert target_item is not None
    assert target_item["needs_manual_review"] is True

    # 5. Работодатель утверждает исправленный балл
    review_resp = await client.post(
        f"/api/v1/testing/open-submissions/{submission_id}/review",
        headers=emp_headers,
        json={
            "score": 0.85,
            "passed": True,
            "notes": "Ручная проверка эксперта: опечатка в синтаксисе учтена, алгоритмическая основа верна.",
        },
    )
    assert review_resp.status_code == 200
    reviewed_item = review_resp.json()
    assert reviewed_item["id"] == submission_id
    assert reviewed_item["score"] == 0.85
    assert reviewed_item["passed"] is True
    assert reviewed_item["needs_manual_review"] is False
    assert reviewed_item["manual_reviewer_notes"] == "Ручная проверка эксперта: опечатка в синтаксисе учтена, алгоритмическая основа верна."
    assert reviewed_item["reviewed_at"] is not None
    assert reviewed_item["reviewed_by"] is not None

    # 6. Решение больше не отображается в очереди на ручную проверку
    pending_after = await client.get(
        "/api/v1/testing/open-submissions/pending-review",
        headers=emp_headers,
    )
    assert pending_after.status_code == 200
    assert not any(item["id"] == submission_id for item in pending_after.json())

    # 7. Несуществующий id возвращает 404
    non_existent_uuid = str(uuid.uuid4())
    not_found_resp = await client.post(
        f"/api/v1/testing/open-submissions/{non_existent_uuid}/review",
        headers=emp_headers,
        json={"score": 0.5, "passed": False},
    )
    assert not_found_resp.status_code == 404

