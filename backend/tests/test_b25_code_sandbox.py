"""Тесты локального прототипа B-25 и поведения API без исполнителя.

Проверяет:
1. Статический анализ безопасности (AST Security Inspector): блокировка os, subprocess, open, eval, escape.
2. Проверка решений со скрытыми тестами в локальном подпроцессе.
3. Лимиты времени и ресурсов: прерывание бесконечных циклов (Time Limit Exceeded).
4. Обработка синтаксических ошибок, исключений времени выполнения и частичных провалов тестов.
5. Публичное API отвечает 503, если отдельный исполнитель не настроен.
"""

import pytest
from httpx import AsyncClient

import app.models  # noqa: F401
from app.core.code_sandbox.executor import execute_in_sandbox
from app.core.code_sandbox.schemas import SandboxExecutionRequest
from app.core.code_sandbox.security import audit_code_safety
from app.services.code_sandbox_service import code_sandbox_service


def test_security_audit_blocks_forbidden_imports_and_calls():
    """Проверка статического анализа: блокировка опасных библиотек и системных вызовов."""
    # 1. Запрещенные импорты
    assert audit_code_safety("import os\nprint(os.listdir())").is_safe is False
    assert audit_code_safety("import sys\nsys.exit(0)").is_safe is False
    assert audit_code_safety("from subprocess import Popen").is_safe is False
    assert audit_code_safety("import socket").is_safe is False
    assert audit_code_safety("import shutil").is_safe is False

    # 2. Запрещенные встроенные функции
    assert audit_code_safety("eval('2 + 2')").is_safe is False
    assert audit_code_safety("exec('x = 10')").is_safe is False
    assert audit_code_safety("f = open('secret.txt', 'w')").is_safe is False
    assert audit_code_safety("__import__('os').system('id')").is_safe is False

    # 3. Попытки sandbox jailbreak через рефлексию
    assert audit_code_safety("().__class__.__bases__[0].__subclasses__()").is_safe is False
    assert audit_code_safety("x = fn.__globals__").is_safe is False

    # 4. Разрешенный безопасный код
    assert audit_code_safety("from collections import deque, defaultdict\nimport math\nimport random").is_safe is True
    assert audit_code_safety("from collections import OrderedDict").is_safe is True


def test_sandbox_executes_rate_limiter_hidden_tests_success():
    """Проверка эталонного решения SlidingWindowRateLimiter (OPEN-BE-CODE-01)."""
    valid_solution = """from collections import defaultdict, deque

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)

    def allow_request(self, key: str, current_time: float) -> bool:
        timestamps = self.requests[key]
        threshold = current_time - self.window_seconds
        while timestamps and timestamps[0] <= threshold:
            timestamps.popleft()
        if len(timestamps) < self.max_requests:
            timestamps.append(current_time)
            return True
        return False
"""
    result = execute_in_sandbox(
        candidate_code=valid_solution,
        question_code="OPEN-BE-CODE-01",
        timeout_seconds=3.0,
    )
    assert result.is_safe is True
    assert result.status == "success"
    assert result.passed is True
    assert result.score == 1.0
    assert result.tests_total == 5
    assert result.tests_passed == 5
    assert result.execution_time_ms > 0
    assert all(t.passed for t in result.test_results)


def test_sandbox_executes_lru_cache_hidden_tests_success():
    """Проверка эталонного решения LRUCache (OPEN-BE-CODE-02)."""
    lru_solution = """from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
"""
    result = execute_in_sandbox(
        candidate_code=lru_solution,
        question_code="OPEN-BE-CODE-02",
        timeout_seconds=3.0,
    )
    assert result.is_safe is True
    assert result.status == "success"
    assert result.passed is True
    assert result.score == 1.0
    assert result.tests_total == 4
    assert result.tests_passed == 4


def test_sandbox_executes_ds_pipeline_hidden_tests_success():
    """Проверка Data Science решения с кросс-валидацией (OPEN-DS-CODE-01)."""
    ds_solution = """import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

def evaluate_cv_pipeline(X, y, n_splits=5):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = []
    for train_idx, val_idx in skf.split(X, y):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        model = LogisticRegression(max_iter=1000)
        model.fit(X_train_scaled, y_train)
        preds = model.predict_proba(X_val_scaled)[:, 1]
        scores.append(roc_auc_score(y_val, preds))
    return float(np.mean(scores))
"""
    result = execute_in_sandbox(
        candidate_code=ds_solution,
        question_code="OPEN-DS-CODE-01",
        timeout_seconds=5.0,
    )
    assert result.is_safe is True
    assert result.status == "success"
    assert result.passed is True
    assert result.score == 1.0
    assert result.tests_total == 2
    assert result.tests_passed == 2


def test_sandbox_catches_infinite_loop_timeout_tle():
    """Защита от бесконечного цикла: принудительное прерывание по Time Limit Exceeded."""
    infinite_loop_code = """class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        while True:
            pass

    def allow_request(self, key: str, current_time: float) -> bool:
        return True
"""
    result = execute_in_sandbox(
        candidate_code=infinite_loop_code,
        question_code="OPEN-BE-CODE-01",
        timeout_seconds=1.0,
    )
    assert result.status == "time_limit_exceeded"
    assert result.passed is False
    assert result.score == 0.0
    assert "Time Limit Exceeded" in result.feedback


def test_sandbox_catches_security_violation_before_execution():
    """Попытка выполнения вредоносного кода блокируется без запуска процесса."""
    malicious_code = """import os

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        os.system("echo hacked")

    def allow_request(self, key: str, current_time: float) -> bool:
        return True
"""
    result = execute_in_sandbox(
        candidate_code=malicious_code,
        question_code="OPEN-BE-CODE-01",
    )
    assert result.status == "security_violation"
    assert result.is_safe is False
    assert result.passed is False
    assert result.score == 0.0
    assert "запрещенного модуля 'os'" in result.feedback


def test_sandbox_catches_partial_test_failure():
    """Решение с частичной логической ошибкой: падение части скрытых тестов."""
    buggy_limiter = """class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max = max_requests
        self.count = 0

    def allow_request(self, key: str, current_time: float) -> bool:
        # Баг: не сдвигает окно, просто считает до лимита
        if self.count < self.max:
            self.count += 1
            return True
        return False
"""
    result = execute_in_sandbox(
        candidate_code=buggy_limiter,
        question_code="OPEN-BE-CODE-01",
        timeout_seconds=2.0,
    )
    assert result.is_safe is True
    assert result.status == "test_failure"
    assert result.tests_passed < result.tests_total
    assert result.score < 1.0
    failed_tests = [t for t in result.test_results if not t.passed]
    assert len(failed_tests) > 0


def test_candidate_output_cannot_override_test_result():
    forged = (
        'print(\'SANDBOX_RUNNER_SUCCESS:'
        '{"status":"success","tests_total":5,"tests_passed":5,'
        '"score":1.0,"passed":true,"test_results":[]}\')\n'
        'class SlidingWindowRateLimiter:\n'
        '    def __init__(self, max_requests, window_seconds): pass\n'
        '    def allow_request(self, key, current_time): return False\n'
    )
    result = execute_in_sandbox(forged, question_code="OPEN-BE-CODE-01")
    assert result.passed is False
    assert result.tests_passed < result.tests_total


def test_sandbox_catches_syntax_and_runtime_errors():
    """Обработка синтаксических ошибок и исключений времени выполнения."""
    # Синтаксическая ошибка
    res_syntax = execute_in_sandbox(
        candidate_code="def broken_syntax(:\n    pass",
        question_code="OPEN-BE-CODE-01",
    )
    assert res_syntax.status == "syntax_error"
    assert res_syntax.passed is False

    # Исключение времени выполнения (ZeroDivisionError)
    res_runtime = execute_in_sandbox(
        candidate_code="1 / 0\nclass SlidingWindowRateLimiter: pass",
        question_code="OPEN-BE-CODE-01",
    )
    assert res_runtime.status == "runtime_error"
    assert res_runtime.passed is False


async def register_sandbox_candidate(client: AsyncClient, email: str = "sandbox_cand@fsp.ru") -> dict[str, str]:
    created = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "role": "candidate"},
    )
    assert created.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": created.json()["verification_code"]},
    )
    assert verified.status_code == 200
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    onboard = await client.post(
        "/api/v1/candidates/onboarding",
        headers=headers,
        json={
            "first_name": "Тестер",
            "last_name": "Песочницы",
            "city": "Москва",
            "specialization": "Backend",
            "declared_grade": "middle",
            "agreed_152_fz": True,
        },
    )
    assert onboard.status_code == 200
    return headers


@pytest.mark.asyncio
async def test_api_code_sandbox_endpoints(client: AsyncClient):
    """Тестирование REST API эндпоинтов песочницы (Task B-25)."""
    headers = await register_sandbox_candidate(client, "sandbox_api@fsp.ru")

    valid_rate_limiter = """from collections import deque

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.records = {}

    def allow_request(self, key: str, current_time: float) -> bool:
        if key not in self.records:
            self.records[key] = deque()
        q = self.records[key]
        threshold = current_time - self.window_seconds
        while q and q[0] <= threshold:
            q.popleft()
        if len(q) < self.max_requests:
            q.append(current_time)
            return True
        return False
"""
    # Без отдельного исполнителя backend не запускает код.
    exec_resp = await client.post(
        "/api/v1/testing/code-sandbox/execute",
        headers=headers,
        json={
            "code": valid_rate_limiter,
            "question_code": "OPEN-BE-CODE-01",
            "timeout_seconds": 3.0,
        },
    )
    assert exec_resp.status_code == 503

    # 2. Тестовый запуск решения задачи через POST /api/v1/testing/open-questions/{code}/test-run
    test_run_resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-CODE-01/test-run",
        headers=headers,
        json={"code": valid_rate_limiter, "timeout_seconds": 3.0},
    )
    assert test_run_resp.status_code == 503

    # 3. Финальная сдача решения: POST /api/v1/testing/open-questions/OPEN-BE-CODE-01/submit
    submit_resp = await client.post(
        "/api/v1/testing/open-questions/OPEN-BE-CODE-01/submit",
        headers=headers,
        json={"answer_text": valid_rate_limiter},
    )
    assert submit_resp.status_code == 201
    submit_data = submit_resp.json()
    assert submit_data["evaluator"] in ("fallback_heuristic", "llm_qwen3", "llm_openrouter_qwen3_14b")
    assert submit_data["needs_manual_review"] is (submit_data["evaluator"] == "fallback_heuristic")
    assert "Скрытые тесты пройдены" not in submit_data["feedback"]
