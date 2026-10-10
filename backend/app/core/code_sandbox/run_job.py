"""Сравнение ответов выполняется отдельно от недоверенного кода."""

import base64
from collections import OrderedDict, defaultdict, deque
import json
import math
import os
import random
import secrets
import statistics
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
SUPPORTED_QUESTIONS = {
    "OPEN-BE-CODE-JR-01", "OPEN-BE-CODE-01", "OPEN-BE-CODE-02", "OPEN-BE-CODE-JR-RE",
    "OPEN-BE-CODE-MID-02",
    "OPEN-BE-CODE-SR-01",
    "OPEN-DS-CODE-JR-01", "OPEN-DS-CODE-JR-RE", "OPEN-DS-CODE-01", "OPEN-DS-CODE-MID-02",
    "OPEN-DS-CODE-SR-01",
}


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


def _orders_expected(case: dict[str, Any]) -> dict[str, int] | str:
    totals: dict[str, int] = {}
    for order in case["orders"]:
        if (not isinstance(order, dict) or not isinstance(order.get("user_id"), str)
                or not order["user_id"] or type(order.get("amount")) is not int
                or order["amount"] <= 0):
            return "ValueError"
        totals[order["user_id"]] = totals.get(order["user_id"], 0) + order["amount"]
    return totals


def _paid_summary_expected(case: dict[str, Any]) -> list[list[Any]]:
    totals: dict[str, tuple[int, int]] = {}
    for row in case["rows"]:
        if row["status"] != "paid" or row["amount"] <= 0:
            continue
        count, total = totals.get(row["client_id"], (0, 0))
        totals[row["client_id"]] = (count + 1, total + row["amount"])
    return [[key, *totals[key]] for key in sorted(totals)]


def _transactions_expected(case: dict[str, Any]) -> list[list[Any]]:
    totals: dict[int, tuple[float, int]] = {}
    for row in case["rows"]:
        if row["status"] != "success":
            continue
        total, count = totals.get(row["user_id"], (0.0, 0))
        totals[row["user_id"]] = (total + row["amount"], count + 1)
    return [[user, total, count] for user, (total, count) in sorted(
        totals.items(), key=lambda item: -item[1][0],
    )]


def _cuped_expected(case: dict[str, Any]) -> list[Any]:
    y, x = case["y"], case["x"]
    variance_x = statistics.variance(x)
    theta = statistics.covariance(y, x) / variance_x if variance_x else 0.0
    mean_x = statistics.mean(x)
    adjusted = [value - theta * (covariate - mean_x) for value, covariate in zip(y, x)]
    variance_y = statistics.variance(y)
    reduction = 1 - statistics.variance(adjusted) / variance_y if variance_y else 0.0
    return [adjusted, reduction, theta]


def _same_result(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and "status" in expected:
        return isinstance(actual, dict) and all(
            _same_result(actual.get(key), value) for key, value in expected.items()
        )
    if isinstance(expected, dict) and "between" in expected:
        lower, upper = expected["between"]
        return type(actual) in (int, float) and math.isfinite(actual) and lower <= actual <= upper
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _same_result(item, target) for item, target in zip(actual, expected)
        )
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return type(actual) in (int, float) and math.isfinite(actual) and math.isclose(
            actual, expected, rel_tol=1e-6, abs_tol=1e-6,
        )
    return type(actual) is type(expected) and actual == expected


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

    if question_code == "OPEN-BE-CODE-JR-01":
        cases.extend([
            {"body": {"item_id": 1, "quantity": 2, "price": 99.0}, "available": True},
            {"body": {"item_id": 1, "quantity": 2, "price": 99.0}, "available": False},
            {"body": {"item_id": 1, "quantity": 0, "price": 99.0}, "available": True},
            {"body": {"item_id": 1, "quantity": 2, "price": -1.0}, "available": True},
        ])
        for _ in range(8):
            cases.append({
                "body": {"item_id": rng.randint(1, 100), "quantity": rng.randint(1, 10),
                         "price": rng.randint(1, 1000) / 10},
                "available": rng.choice([True, False]),
            })
        return [(case, {"status": 422} if case["body"]["quantity"] <= 0 or case["body"]["price"] <= 0
                 else {"status": 201, "order_id": 123, "result": "created"} if case["available"]
                 else {"status": 400, "detail": "Out of stock"}) for case in cases]

    if question_code == "OPEN-BE-CODE-JR-RE":
        cases.extend([
            {"orders": [{"user_id": "a", "amount": 3}, {"user_id": "a", "amount": 7}, {"user_id": "b", "amount": 2}]},
            {"orders": []},
            {"orders": [{"user_id": "a", "amount": 0}]},
            {"orders": [{"user_id": "a", "amount": True}]},
            {"orders": [{"user_id": "a"}]},
        ])
        for _ in range(7):
            orders = [{"user_id": rng.choice(["a", "b", "c"]), "amount": rng.randint(1, 100)}
                      for _ in range(rng.randint(2, 15))]
            cases.append({"orders": orders})
        return [(case, _orders_expected(case)) for case in cases]

    if question_code == "OPEN-BE-CODE-MID-02":
        cases.extend([
            {"values": [1, 2, 3], "fail_value": None},
            {"values": [1, 2, 3], "fail_value": 2},
            {"values": [4, 5], "fail_value": None, "slow_value": 4},
        ])
        for _ in range(9):
            values = list(range(1, rng.randint(3, 7)))
            cases.append({"values": values, "fail_value": rng.choice([None, *values])})
        return [(case, [case["values"], True]) for case in cases]

    if question_code == "OPEN-BE-CODE-SR-01":
        for index in range(12):
            cases.append({
                "kind": ("normal", "breaker", "recovery", "capacity")[index % 4],
                "max_concurrency": rng.randint(1, 3),
                "queue_size": rng.randint(1, 4),
                "failure_threshold": 2,
                "recovery_timeout": 0.1,
            })
        return [(case, True) for case in cases]

    if question_code == "OPEN-DS-CODE-JR-RE":
        cases.extend([
            {"rows": [{"client_id": "a", "amount": 3, "status": "paid"},
                      {"client_id": "a", "amount": 7, "status": "paid"},
                      {"client_id": "b", "amount": 10, "status": "pending"}]},
            {"rows": []},
            {"rows": [{"client_id": "a", "amount": 0, "status": "paid"}]},
        ])
        for _ in range(9):
            rows = [{"client_id": rng.choice(["a", "b", "c"]),
                     "amount": rng.randint(-5, 50), "status": rng.choice(["paid", "paid", "pending"])}
                    for _ in range(rng.randint(3, 15))]
            cases.append({"rows": rows})
        return [(case, _paid_summary_expected(case)) for case in cases]

    if question_code == "OPEN-DS-CODE-JR-01":
        cases.extend([
            {"rows": [
                {"transaction_id": 1, "user_id": 9, "category": "books", "status": "success", "amount": 12.0, "created_at": "2026-01-01"},
                {"transaction_id": 2, "user_id": 9, "category": "books", "status": "success", "amount": 5.0, "created_at": "2026-01-02"},
                {"transaction_id": 3, "user_id": 3, "category": "food", "status": "failed", "amount": 40.0, "created_at": "2026-01-03"},
            ]},
            {"rows": []},
        ])
        for _ in range(10):
            rows = [{
                "transaction_id": index + 1, "user_id": rng.choice([1, 2, 3, 4]),
                "category": rng.choice(["books", "food"]),
                "status": rng.choice(["success", "success", "failed"]),
                "amount": rng.randint(1, 100) + index / 100,
                "created_at": f"2026-01-{index + 1:02d}",
            } for index in range(rng.randint(4, 16))]
            cases.append({"rows": rows})
        return [(case, _transactions_expected(case)) for case in cases]

    if question_code == "OPEN-DS-CODE-MID-02":
        cases.extend([
            {"y": [2, 4, 6, 8], "x": [1, 2, 3, 4]},
            {"y": [2, 4, 7, 9], "x": [3, 3, 3, 3]},
            {"y": [5, 5, 5, 5], "x": [1, 2, 3, 4]},
        ])
        for _ in range(9):
            x = [rng.randint(1, 30) for _ in range(16)]
            y = [round(2.5 * value + rng.uniform(-5, 5), 4) for value in x]
            cases.append({"x": x, "y": y})
        return [(case, _cuped_expected(case)) for case in cases]

    if question_code == "OPEN-DS-CODE-01":
        for index in range(12):
            signal = index % 3 != 0
            rows, labels = [], []
            for row in range(60):
                label = row % 2
                labels.append(label)
                rows.append([
                    rng.gauss(3 if label else -3, 0.5) if signal else rng.gauss(0, 1),
                    rng.gauss(0, 1),
                ])
            cases.append({"X": rows, "y": labels, "n_splits": 3})
        return [(case, {"between": [0.85, 1.0] if index % 3 != 0 else [0.05, 0.95]})
                for index, case in enumerate(cases)]

    if question_code == "OPEN-DS-CODE-SR-01":
        for _ in range(12):
            train_x, train_y, test_x, test_y = [], [], [], []
            for rows, labels, count in ((train_x, train_y, 80), (test_x, test_y, 30)):
                for row in range(count):
                    label = row % 2
                    labels.append(label)
                    rows.append([rng.gauss(2.5 if label else -2.5, 0.8), rng.gauss(0, 1)])
            cases.append({"train_x": train_x, "train_y": train_y,
                          "test_x": test_x, "test_y": test_y})
        return [(case, [True, True, True, True]) for case in cases]

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
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
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
        elif question_code == "OPEN-BE-CODE-02":
            if isinstance(actual, list):
                actual = [None if value == -1 and target is None else value
                          for value, target in zip(actual, expected)]
            passed = (isinstance(actual, list) and len(actual) == len(expected)
                      and all((value is None or type(value) is int) and value == target
                              for value, target in zip(actual, expected)))
        else:
            passed = _same_result(actual, expected)
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
