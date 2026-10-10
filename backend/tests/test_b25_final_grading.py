"""A fluent rubric answer cannot hide code that fails the functional checks."""

import pytest

from app.core.code_sandbox.schemas import SandboxExecutionResponse
from app.core.open_question_bank import get_open_question_by_code
from app.services import open_question_service
from app.services.code_sandbox_service import code_sandbox_service


@pytest.mark.asyncio
@pytest.mark.parametrize("functional,model,expected", [
    (0.0, 1.0, 0.0),
    (0.6, 0.9, 0.6),
    (1.0, 0.4, 0.4),
    (1.0, 0.9, 0.9),
])
async def test_grade_is_bounded_by_code_and_rubric(monkeypatch, functional, model, expected):
    question = get_open_question_by_code("OPEN-BE-CODE-01")

    async def fake_sandbox(_code, _answer):
        return SandboxExecutionResponse(
            status="success" if functional == 1 else "test_failure",
            is_safe=True, passed=functional >= 0.7, score=functional,
            tests_total=10, tests_passed=int(functional * 10),
        )

    async def fake_model(_question, _answer, _client=None):
        return {"score": model, "passed": model >= 0.7, "feedback": "Разбор решения",
                "criterion_scores": {}, "evaluator": "llm_test", "needs_manual_review": False}

    monkeypatch.setattr(code_sandbox_service, "evaluate_question_code", fake_sandbox)
    monkeypatch.setattr(open_question_service, "_evaluate_with_ml", fake_model)
    result = await open_question_service.evaluate_open_answer(question, "candidate code")
    assert result["score"] == expected
    assert result["passed"] is (expected >= 0.7)
    assert result["criterion_scores"]["Функциональные тесты"] == functional
    assert "code_sandbox_b25" in result["evaluator"]


@pytest.mark.asyncio
async def test_missing_functional_checks_cannot_be_treated_as_success(monkeypatch):
    question = get_open_question_by_code("OPEN-BE-CODE-01")

    async def empty_sandbox(_code, _answer):
        return SandboxExecutionResponse(
            status="success", is_safe=True, passed=True, score=1,
            tests_total=0, tests_passed=0,
        )

    monkeypatch.setattr(code_sandbox_service, "evaluate_question_code", empty_sandbox)
    with pytest.raises(RuntimeError):
        await open_question_service.evaluate_open_answer(question, "candidate code")
