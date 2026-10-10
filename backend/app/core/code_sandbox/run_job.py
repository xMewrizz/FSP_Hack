"""Сравнение ответов выполняется отдельно от недоверенного кода."""

import base64
from collections import OrderedDict, defaultdict, deque
import json
import os
import random
import secrets
import subprocess
import sys
import tempfile
import time
from typing import Any

from app.core.code_sandbox.schemas import SandboxExecutionResponse, TestCaseResult
from app.core.code_sandbox.security import audit_code_safety


WORKER_PREFIX = "SANDBOX_WORKER_RESULT:"
RESULT_PREFIX = "SANDBOX_JOB_RESULT:"
MAX_WORKER_OUTPUT = 64 * 1024
SUPPORTED_QUESTIONS = {"OPEN-BE-CODE-01", "OPEN-BE-CODE-02"}


def _rate_limiter_expected(case: dict[str, Any]) -> list[bool]:
    history: dict[str, deque[float]] = defaultdict(deque)
    results = []
    for key, timestamp in case["requests"]:
        threshold = timestamp - case["window_seconds"]
        while history[key] and history[key][0] <= threshold:
            history[key].popleft()
        allowed = len(history[key]) < case["max_requests"]
        if allowed:
            history[key].append(timestamp)
        results.append(allowed)
    return results


def _lru_expected(case: dict[str, Any]) -> list[int | None]:
    cache: OrderedDict[str, int] = OrderedDict()
    results = []
    for operation in case["operations"]:
        if operation[0] == "put":
            _, key, value = operation
            if key in cache:
                cache.move_to_end(key)
            cache[key] = value
            if len(cache) > case["capacity"]:
                cache.popitem(last=False)
        else:
            key = operation[1]
            if key not in cache:
                results.append(None)
            else:
                cache.move_to_end(key)
                results.append(cache[key])
    return results


def build_cases(question_code: str, rng: random.Random | None = None) -> list[tuple[dict[str, Any], list]]:
    """Точные входные данные выбираются заново для каждой попытки."""
    if question_code not in SUPPORTED_QUESTIONS:
        raise ValueError("Для этого задания нет проверки кода")
    rng = rng or secrets.SystemRandom()
    cases: list[dict[str, Any]] = []
    if question_code == "OPEN-BE-CODE-01":
        cases.extend([
            {"max_requests": 2, "window_seconds": 5.0,
             "requests": [["a", 1.0], ["a", 2.0], ["a", 3.0], ["a", 8.0]]},
            {"max_requests": 1, "window_seconds": 10.0,
             "requests": [["a", 1.0], ["b", 1.0], ["a", 2.0], ["b", 12.0]]},
        ])
        for _ in range(10):
            timestamp = float(rng.randint(1, 10))
            requests = []
            for _ in range(rng.randint(12, 22)):
                timestamp += rng.choice([0.0, 0.25, 1.0, 3.0, 7.0])
                requests.append([rng.choice(["a", "b", "c"]), timestamp])
            cases.append({
                "max_requests": rng.randint(1, 4),
                "window_seconds": float(rng.randint(2, 12)),
                "requests": requests,
            })
        return [(case, _rate_limiter_expected(case)) for case in cases]

    cases.extend([
        {"capacity": 2, "operations": [
            ["put", "a", 1], ["put", "b", 2], ["get", "a"],
            ["put", "c", 3], ["get", "b"], ["get", "a"], ["get", "c"]]},
        {"capacity": 1, "operations": [
            ["get", "missing"], ["put", "a", 1], ["put", "a", 2],
            ["get", "a"], ["put", "b", 3], ["get", "a"]]},
    ])
    for _ in range(10):
        operations = []
        for _ in range(rng.randint(12, 25)):
            key = rng.choice(["a", "b", "c", "d", "e"])
            if rng.random() < 0.55:
                operations.append(["put", key, rng.randint(1, 1000)])
            else:
                operations.append(["get", key])
        cases.append({"capacity": rng.randint(1, 4), "operations": operations})
    return [(case, _lru_expected(case)) for case in cases]


def _drop_privileges() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_WORKER_OUTPUT, MAX_WORKER_OUTPUT))
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)


def _failed(status: str, total: int, started: float, feedback: str) -> SandboxExecutionResponse:
    return SandboxExecutionResponse(
        status=status, is_safe=status != "security_violation", passed=False,
        score=0.0, tests_total=total, tests_passed=0,
        execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
        feedback=feedback,
    )


def grade_code(code: str, question_code: str, timeout_seconds: float) -> SandboxExecutionResponse:
    audit = audit_code_safety(code)
    if not audit.is_safe:
        status = "syntax_error" if audit.violation_node == "SyntaxError" else "security_violation"
        return SandboxExecutionResponse(
            status=status, is_safe=False, passed=False, score=0.0,
            tests_total=0, tests_passed=0, execution_time_ms=0.0,
            feedback=audit.error_message or "Код не прошёл проверку",
        )

    cases = build_cases(question_code)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="fsp_job_") as temporary:
        os.chmod(temporary, 0o755)
        solution_path = os.path.join(temporary, "solution.py")
        with open(solution_path, "w", encoding="utf-8") as source:
            source.write(code)
        os.chmod(solution_path, 0o644)

        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": "/app",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        payload = json.dumps({
            "question_code": question_code,
            "cases": [case for case, _ in cases],
        })
        with tempfile.TemporaryFile(mode="w+b") as output, tempfile.TemporaryFile(mode="w+b") as errors:
            process = subprocess.Popen(
                [sys.executable, "-m", "app.core.code_sandbox.candidate_worker"],
                cwd=temporary, env=environment, stdin=subprocess.PIPE,
                stdout=output, stderr=errors, text=True, preexec_fn=_drop_privileges,
            )
            try:
                process.communicate(input=payload, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return _failed("time_limit_exceeded", len(cases), started, "Превышено время выполнения")
            output.seek(0)
            worker_output = output.read(MAX_WORKER_OUTPUT).decode("utf-8", errors="replace")

    report = None
    if process.returncode == 0:
        for line in reversed(worker_output.splitlines()):
            if line.startswith(WORKER_PREFIX):
                try:
                    report = json.loads(line[len(WORKER_PREFIX):])
                except json.JSONDecodeError:
                    pass
                break
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        return _failed("runtime_error", len(cases), started, "Решение не вернуло результат")

    actual_results = report["results"]
    tests = []
    for index, (_, expected) in enumerate(cases):
        actual = actual_results[index] if index < len(actual_results) else None
        if question_code == "OPEN-BE-CODE-01":
            passed = (isinstance(actual, list) and len(actual) == len(expected)
                      and all(type(value) is bool and value == target
                              for value, target in zip(actual, expected)))
        else:
            if isinstance(actual, list):
                actual = [None if value == -1 and target is None else value
                          for value, target in zip(actual, expected)]
            passed = (isinstance(actual, list) and len(actual) == len(expected)
                      and all((value is None or type(value) is int) and value == target
                              for value, target in zip(actual, expected)))
        tests.append(TestCaseResult(name=f"case_{index + 1}", passed=passed))
    passed_count = sum(test.passed for test in tests)
    total = len(tests)
    return SandboxExecutionResponse(
        status="success" if passed_count == total else "test_failure",
        is_safe=True, passed=passed_count == total, score=round(passed_count / total, 2),
        tests_total=total, tests_passed=passed_count,
        execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
        test_results=tests,
        feedback=f"Пройдено проверок: {passed_count}/{total}",
    )


def main() -> None:
    code = base64.b64decode(os.environ["SANDBOX_CODE_B64"], validate=True).decode("utf-8")
    result = grade_code(
        code=code,
        question_code=os.environ["SANDBOX_QUESTION_CODE"],
        timeout_seconds=float(os.environ["SANDBOX_TIMEOUT_SECONDS"]),
    )
    print(RESULT_PREFIX + result.model_dump_json(), flush=True)


if __name__ == "__main__":
    main()
