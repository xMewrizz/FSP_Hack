import pytest
import httpx
from httpx import AsyncClient

from app.core.open_question_bank import (
    OPEN_QUESTIONS,
    get_open_question_by_code,
)
from app.services.open_question_service import get_public_open_questions
from app.core.question_variants import prepared_variants


@pytest.fixture(autouse=True)
def fake_functional_checks(monkeypatch):
    """These API tests exercise grading flow; Docker cases have separate integration tests."""
    from app.core.code_sandbox.schemas import SandboxExecutionResponse
    from app.services.code_sandbox_service import code_sandbox_service

    async def evaluate(_question_code, code, _timeout_seconds=3.0):
        valid = "broken syntax" not in code
        return SandboxExecutionResponse(
            status="success" if valid else "syntax_error", is_safe=valid,
            passed=valid, score=1.0 if valid else 0.0,
            tests_total=12, tests_passed=12 if valid else 0,
        )

    monkeypatch.setattr(code_sandbox_service, "evaluate_question_code", evaluate)


def test_open_questions_bank_structure():
    assert len(OPEN_QUESTIONS) >= 33
    codes = [q["code"] for q in OPEN_QUESTIONS]
    assert len(codes) == len(set(codes))

    be_questions = [q for q in OPEN_QUESTIONS if q["specialization"] == "Backend"]
    ds_questions = [q for q in OPEN_QUESTIONS if q["specialization"] == "Data Science / ML"]
    assert len(be_questions) >= 17
    assert len(ds_questions) >= 16

    # Проверка распределения по грейдам
    for spec_questions in (be_questions, ds_questions):
        juniors = [q for q in spec_questions if q["grade"] == "junior"]
        middles = [q for q in spec_questions if q["grade"] == "middle"]
        seniors = [q for q in spec_questions if q["grade"] == "senior"]
        assert len(juniors) >= 4
        assert len(middles) >= 6
        assert len(seniors) >= 6

    # Проверка структуры каждого вопроса
    for q in OPEN_QUESTIONS:
        assert q["code"].startswith("OPEN-")
        assert q["specialization"] in ("Backend", "Data Science / ML")
        assert q["grade"] in ("junior", "middle", "senior")
        assert q["question_type"] in ("free_text", "code")
        assert len(q["skill"]) > 3
        assert len(q["acceptable_solutions"]) >= 2
        assert len(q["rubric_criteria"]) >= 3
        assert len(q["reference_solution"]) > 20
        assert len(q["question_text"]) > 20

    public = get_public_open_questions()
    assert len(public) == len(OPEN_QUESTIONS)
    for pub in public:
        assert "reference_solution" not in pub
        assert "rubric_criteria" in pub
        assert "code" in pub
        assert "skill" in pub
        assert "acceptable_solutions" not in pub

    # Проверка фильтра по грейду
    juniors_pub = get_public_open_questions(grade="junior")
    assert len(juniors_pub) >= 8
    seniors_pub = get_public_open_questions(grade="senior")
    assert len(seniors_pub) >= 12
    ds_middles_pub = get_public_open_questions(specialization="Data Science / ML", grade="middle")
    assert len(ds_middles_pub) >= 6


@pytest.mark.asyncio
async def test_open_questions_endpoints_grade_filter(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "filter_questions@example.com")
    resp = await client.get("/api/v1/testing/open-questions?grade=junior", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 8
    for it in items:
        assert it["grade"] == "junior"
        assert "skill" in it
        assert "acceptable_solutions" not in it

    resp_sr = await client.get("/api/v1/testing/open-questions?specialization=Backend&grade=senior", headers=headers)
    assert resp_sr.status_code == 200
    items_sr = resp_sr.json()
    assert len(items_sr) >= 6
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
    consent = await client.put(
        "/api/v1/candidates/profile",
        headers=headers,
        json={"agreed_test_confidentiality": True},
    )
    assert consent.status_code == 200
    return headers


async def complete_choices(client: AsyncClient, headers: dict[str, str], assessment_id: str, skills: list[dict]):
    for skill in skills:
        started = await client.post(
            f"/api/v1/testing/roadmap/{assessment_id}/skills/{skill['code']}/start", headers=headers,
        )
        assert started.status_code == 201
        answers = []
        for question in started.json()["questions"]:
            variant = next(item for item in prepared_variants(question["code"].split("-V")[0]) if item["code"] == question["code"])
            answers.append({"question_id": question["id"], "selected_answers": variant["correct_answers"]})
        submitted = await client.post(
            f"/api/v1/testing/{started.json()['session_id']}/submit", headers=headers,
            json={"answers": answers},
        )
        assert submitted.status_code == 200, submitted.text


@pytest.mark.asyncio
async def test_list_open_questions_api(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "list_questions@example.com")
    denied = await client.get("/api/v1/testing/open-questions")
    assert denied.status_code == 401
    resp = await client.get("/api/v1/testing/open-questions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    for item in data:
        assert "reference_solution" not in item
        assert "code" in item
        assert "rubric_criteria" in item


@pytest.mark.asyncio
async def test_get_single_open_question_api(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "single_question@example.com")
    resp = await client.get("/api/v1/testing/open-questions/OPEN-BE-ARCH-01", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "OPEN-BE-ARCH-01"
    assert data["question_type"] == "free_text"
    assert "reference_solution" not in data

    not_found = await client.get("/api/v1/testing/open-questions/OPEN-NON-EXISTENT", headers=headers)
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
    assert body["evaluator"] in ("llm_qwen3", "llm_openrouter_qwen3_14b", "fallback_heuristic")
    assert body["needs_manual_review"] is True or body["evaluator"] in ("llm_qwen3", "llm_openrouter_qwen3_14b")
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

    # 3. Обычный работодатель не видит чужие ответы и не может их оценивать.
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

    denied_pending = await client.get(
        "/api/v1/testing/open-submissions/pending-review", headers=emp_headers,
    )
    denied_review = await client.post(
        f"/api/v1/testing/open-submissions/{submission_id}/review",
        headers=emp_headers,
        json={"score": 1.0, "passed": True},
    )
    assert denied_pending.status_code == 403
    assert denied_review.status_code == 403

    # В тестовой базе назначаем отдельному пользователю роль администратора.
    from sqlalchemy import select
    from app.core.constants import UserRole
    from app.models.user import User
    from conftest import TestingSessionLocal

    async with TestingSessionLocal() as db:
        reviewer = (await db.execute(select(User).where(User.email == "lead_ds_reviewer@corp.ru"))).scalar_one()
        reviewer.role = UserRole.ADMIN
        await db.commit()

    # 4. Только администратор видит очередь ручной проверки.
    pending_resp = await client.get(
        "/api/v1/testing/open-submissions/pending-review",
        headers=emp_headers,
    )
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    target_item = next((item for item in pending_list if item["id"] == submission_id), None)
    assert target_item is not None
    assert target_item["needs_manual_review"] is True

    # 5. Ручная оценка не может отменить провал скрытых тестов.
    review_resp = await client.post(
        f"/api/v1/testing/open-submissions/{submission_id}/review",
        headers=emp_headers,
        json={
            "score": 0.85,
            "passed": True,
            "notes": "Синтаксическая ошибка требует нового решения.",
        },
    )
    assert review_resp.status_code == 200
    reviewed_item = review_resp.json()
    assert reviewed_item["id"] == submission_id
    assert reviewed_item["score"] == 0.0
    assert reviewed_item["passed"] is False
    assert reviewed_item["needs_manual_review"] is False
    assert reviewed_item["manual_reviewer_notes"] == "Синтаксическая ошибка требует нового решения."
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


@pytest.mark.asyncio
async def test_assigned_open_answers_gate_grade_and_reject_reuse(client: AsyncClient, monkeypatch):
    from app.services import open_question_service

    class FakeMLClient:
        async def post(self, *_args, **_kwargs):
            return httpx.Response(200, json={
                "score": 1.0, "passed": True, "feedback": "Критерии выполнены",
                "criterion_scores": {}, "evaluator": "llm_test", "needs_manual_review": False,
            })

        async def aclose(self):
            pass

    monkeypatch.setattr(open_question_service.httpx, "AsyncClient", lambda **_kwargs: FakeMLClient())
    headers = await open_test_candidate_headers(client, "assigned-open@example.com")
    created = await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "middle"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    codes = [item["code"] for item in created.json()["open_questions"]]
    assert codes == ["OPEN-BE-ARCH-01", "OPEN-BE-CODE-01", "OPEN-BE-WORK-MID-01"]

    unassigned = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-ARCH-JR-01/submit", headers=headers,
        json={"assessment_id": assessment_id, "answer_text": "Описание решения"},
    )
    assert unassigned.status_code == 400

    for code in codes:
        saved = await client.post(
            f"/api/v1/testing/open-questions/{code}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Полное решение"},
        )
        assert saved.status_code == 201, saved.text
        assert saved.json()["assessment_id"] == assessment_id
        duplicate = await client.post(
            f"/api/v1/testing/open-questions/{code}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Другой ответ"},
        )
        assert duplicate.status_code == 409

    before = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert before["status"] == "in_progress"
    assert before["verified_grade"] is None

    await complete_choices(client, headers, assessment_id, before["skills"])

    complete = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert complete["status"] == "completed"
    assert complete["verified_grade"] == "middle"
    assert complete["percentage"] == 100.0
    assert [item["status"] for item in complete["open_questions"]] == ["completed"] * 3


@pytest.mark.asyncio
async def test_queued_answers_survive_navigation_and_grade_waits_for_evaluation(client: AsyncClient, monkeypatch):
    import uuid
    from datetime import datetime, timedelta, timezone
    from app.services import open_question_queue
    from conftest import TestingSessionLocal
    from app.models.test import GradeAssessment, OpenQuestionSubmission

    monkeypatch.setattr(open_question_queue, "AsyncSessionLocal", TestingSessionLocal)

    async def fake_evaluate(_question, _answer):
        return {
            "score": 0.8, "passed": True, "feedback": "Проверено",
            "criterion_scores": {}, "evaluator": "llm_test", "needs_manual_review": False,
        }

    monkeypatch.setattr(open_question_queue, "evaluate_open_answer", fake_evaluate)
    headers = await open_test_candidate_headers(client, "queued-open@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    codes = [item["code"] for item in created["open_questions"]]
    assert len(codes) > 1
    queued = []
    for code in codes:
        response = await client.post(
            f"/api/v1/testing/open-questions/{code}/queue", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": f"Ответ на {code}"},
        )
        assert response.status_code == 202, response.text
        assert response.json()["evaluation_status"] == "queued"
        queued.append(response.json())
    history = (await client.get("/api/v1/testing/open-submissions", headers=headers)).json()
    assert {item["id"] for item in queued} <= {item["id"] for item in history}
    await complete_choices(client, headers, assessment_id, created["skills"])
    before = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert before["verified_grade"] is None
    assert before["status"] == "pending_review"
    assert all(item["status"] == "queued" for item in before["open_questions"])

    # Evaluation can finish after the three-day window without discarding answers
    # that the candidate submitted on time.
    async with TestingSessionLocal() as db:
        assessment = await db.get(GradeAssessment, uuid.UUID(assessment_id))
        assessment.created_at = datetime.now(timezone.utc) - timedelta(days=4)
        await db.commit()
    waiting = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert waiting["status"] == "pending_review"

    for item in queued:
        async with TestingSessionLocal() as db:
            submission = await db.get(OpenQuestionSubmission, uuid.UUID(item["id"]))
            submission.evaluation_status = "evaluating"
            await db.commit()
        await open_question_queue.process_queued_submission(submission.id)
    after = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert after["verified_grade"] == "junior"
    assert all(item["status"] == "completed" for item in after["open_questions"])


@pytest.mark.asyncio
async def test_assessment_waits_only_after_every_open_answer_is_submitted(client: AsyncClient):
    headers = await open_test_candidate_headers(client, "open-after-choices@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    await complete_choices(client, headers, assessment_id, created["skills"])
    codes = [item["code"] for item in created["open_questions"]]

    first = await client.post(
        f"/api/v1/testing/open-questions/{codes[0]}/queue", headers=headers,
        json={"assessment_id": assessment_id, "answer_text": "Первый ответ"},
    )
    assert first.status_code == 202
    partial = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert partial["status"] == "in_progress"

    second = await client.post(
        f"/api/v1/testing/open-questions/{codes[1]}/queue", headers=headers,
        json={"assessment_id": assessment_id, "answer_text": "Второй ответ"},
    )
    assert second.status_code == 202
    complete = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert complete["status"] == "pending_review"


@pytest.mark.asyncio
async def test_failed_background_check_keeps_answer_for_retry(client: AsyncClient, monkeypatch):
    import uuid
    from datetime import datetime, timedelta, timezone
    from app.services import open_question_queue
    from app.services.open_question_service import _local_fallback_eval
    from app.models.test import GradeAssessment, OpenQuestionSubmission
    from conftest import TestingSessionLocal

    monkeypatch.setattr(open_question_queue, "AsyncSessionLocal", TestingSessionLocal)

    async def unavailable(question, answer):
        return _local_fallback_eval(question, answer)

    monkeypatch.setattr(open_question_queue, "evaluate_open_answer", unavailable)
    headers = await open_test_candidate_headers(client, "queued-fail@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    code = created["open_questions"][0]["code"]
    response = await client.post(
        f"/api/v1/testing/open-questions/{code}/queue", headers=headers,
        json={"assessment_id": created["id"], "answer_text": "Мой сохранённый ответ"},
    )
    assert response.status_code == 202
    for other in created["open_questions"][1:]:
        queued = await client.post(
            f"/api/v1/testing/open-questions/{other['code']}/queue", headers=headers,
            json={"assessment_id": created["id"], "answer_text": "Второй ответ"},
        )
        assert queued.status_code == 202
    await complete_choices(client, headers, created["id"], created["skills"])
    submission_id = uuid.UUID(response.json()["id"])
    async with TestingSessionLocal() as db:
        submission = await db.get(OpenQuestionSubmission, submission_id)
        submission.evaluation_status = "evaluating"
        await db.commit()
    await open_question_queue.process_queued_submission(submission_id)
    history = (await client.get("/api/v1/testing/open-submissions", headers=headers)).json()
    saved = next(item for item in history if item["id"] == str(submission_id))
    assert saved["answer_text"] == "Мой сохранённый ответ"
    assert saved["evaluation_status"] == "failed"
    assert saved["score"] == 0
    async with TestingSessionLocal() as db:
        assessment = await db.get(GradeAssessment, uuid.UUID(created["id"]))
        assert assessment.status == "pending_review"
        assessment.created_at = datetime.now(timezone.utc) - timedelta(days=4)
        await db.commit()
    retried = await client.post(
        f"/api/v1/testing/open-submissions/{submission_id}/queue-retry", headers=headers,
    )
    assert retried.status_code == 202
    assert retried.json()["evaluation_status"] == "queued"


@pytest.mark.asyncio
async def test_low_model_score_finishes_grade_without_manual_queue(client: AsyncClient, monkeypatch):
    from app.services import open_question_service
    class FakeMLClient:
        async def post(self, _url, json):
            low = json["question_code"].endswith("ARCH-JR-01")
            return httpx.Response(200, json={
                "score": 0.4 if low else 1.0,
                "passed": not low,
                "feedback": "Автоматическая оценка",
                "criterion_scores": {}, "evaluator": "llm_test", "needs_manual_review": False,
            })

        async def aclose(self):
            pass

    monkeypatch.setattr(open_question_service.httpx, "AsyncClient", lambda **_kwargs: FakeMLClient())
    headers = await open_test_candidate_headers(client, "manual-grade@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    await complete_choices(client, headers, assessment_id, created["skills"])
    assert (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()["verified_grade"] is None

    submissions = []
    for item in created["open_questions"]:
        response = await client.post(
            f"/api/v1/testing/open-questions/{item['code']}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Решение кандидата"},
        )
        assert response.status_code == 201, response.text
        submissions.append(response.json())
    assert submissions[0]["needs_manual_review"] is False
    complete = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert complete["status"] == "completed"
    assert complete["verified_grade"] is None
    assert complete["passed"] is False


@pytest.mark.asyncio
async def test_failing_code_cannot_confirm_grade_even_if_model_gives_full_score(client: AsyncClient, monkeypatch):
    from app.core.code_sandbox.schemas import SandboxExecutionResponse
    from app.services import open_question_service
    from app.services.code_sandbox_service import code_sandbox_service

    async def fake_model(_question, _answer, _client=None):
        return {"score": 1.0, "passed": True, "feedback": "Разбор ответа",
                "criterion_scores": {}, "evaluator": "llm_test", "needs_manual_review": False}

    async def failing_code(_code, _answer, _timeout_seconds=3.0):
        return SandboxExecutionResponse(
            status="test_failure", is_safe=True, passed=False, score=0.0,
            tests_total=10, tests_passed=0,
        )

    monkeypatch.setattr(open_question_service, "_evaluate_with_ml", fake_model)
    monkeypatch.setattr(code_sandbox_service, "evaluate_question_code", failing_code)
    headers = await open_test_candidate_headers(client, "failing-code-grade@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    await complete_choices(client, headers, assessment_id, created["skills"])
    for item in created["open_questions"]:
        response = await client.post(
            f"/api/v1/testing/open-questions/{item['code']}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Решение кандидата"},
        )
        assert response.status_code == 201, response.text
        if item["question_type"] == "code":
            assert response.json()["score"] == 0.0
    roadmap = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert roadmap["status"] == "completed"
    assert roadmap["verified_grade"] is None
    assert roadmap["passed"] is False


@pytest.mark.asyncio
async def test_unavailable_evaluator_does_not_lock_assessment_answer(client: AsyncClient, monkeypatch):
    from app.services import open_question_service

    class FakeMLClient:
        async def post(self, *_args, **_kwargs):
            return httpx.Response(503)

        async def aclose(self):
            pass

    monkeypatch.setattr(open_question_service.httpx, "AsyncClient", lambda **_kwargs: FakeMLClient())
    headers = await open_test_candidate_headers(client, "retry-open@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    code = created["open_questions"][0]["code"]
    for _ in range(2):
        response = await client.post(
            f"/api/v1/testing/open-questions/{code}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Описание технического решения"},
        )
        assert response.status_code == 503
    roadmap = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert roadmap["open_questions"][0]["status"] == "not_started"


@pytest.mark.asyncio
async def test_candidate_can_recheck_legacy_pending_answer(client: AsyncClient, monkeypatch):
    from app.services import open_question_service

    class FakeMLClient:
        pending = True

        async def post(self, *_args, **_kwargs):
            return httpx.Response(200, json={
                "score": 0.75 if self.pending else 1.0,
                "passed": True,
                "feedback": "Проверено",
                "criterion_scores": {},
                "evaluator": "llm_test",
                "needs_manual_review": self.pending,
            })

        async def aclose(self):
            pass

    fake = FakeMLClient()
    monkeypatch.setattr(open_question_service.httpx, "AsyncClient", lambda **_kwargs: fake)
    headers = await open_test_candidate_headers(client, "recheck-open@example.com")
    created = (await client.post("/api/v1/testing/roadmap", headers=headers, json={"target_grade": "junior"})).json()
    assessment_id = created["id"]
    await complete_choices(client, headers, assessment_id, created["skills"])
    saved = []
    for item in created["open_questions"]:
        response = await client.post(
            f"/api/v1/testing/open-questions/{item['code']}/submit", headers=headers,
            json={"assessment_id": assessment_id, "answer_text": "Описание технического решения"},
        )
        assert response.status_code == 201
        saved.append(response.json())
    assert (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()["status"] == "pending_review"
    stranger = await open_test_candidate_headers(client, "other-recheck@example.com")
    denied = await client.post(
        f"/api/v1/testing/open-submissions/{saved[0]['id']}/retry-evaluation", headers=stranger,
    )
    assert denied.status_code == 404
    fake.pending = False
    for item in saved:
        response = await client.post(
            f"/api/v1/testing/open-submissions/{item['id']}/retry-evaluation", headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["needs_manual_review"] is False
    roadmap = (await client.get(f"/api/v1/testing/roadmap/{assessment_id}", headers=headers)).json()
    assert roadmap["status"] == "completed"
    assert roadmap["verified_grade"] == "junior"
