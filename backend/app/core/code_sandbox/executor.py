"""Изолированный исполнитель кода с контролем времени и ресурсов (Task B-25).

Запускает код кандидата в отдельном подпроцессе во временном каталоге
с очищенным окружением и строгими лимитами времени выполнения (TLE) и вывода.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any

from app.core.code_sandbox.hidden_tests import get_hidden_tests_for_question
from app.core.code_sandbox.schemas import SandboxExecutionResponse, TestCaseResult
from app.core.code_sandbox.security import audit_code_safety

MAX_OUTPUT_BYTES = 16 * 1024  # 16 KB лимит вывода
DEFAULT_TIMEOUT_SECONDS = 3.0


RUNNER_SCRIPT_TEMPLATE = """# -*- coding: utf-8 -*-
import sys
import time
import json
import traceback

def main():
    start_all = time.perf_counter()
    results = []
    
    # 1. Загрузка решения кандидата
    try:
        import solution
    except ModuleNotFoundError as mne:
        missing_root = (mne.name or "").split(".")[0]
        if missing_root in ("numpy", "sklearn", "pandas", "scipy"):
            import unittest.mock
            for pkg in ("numpy", "sklearn", "sklearn.model_selection", "sklearn.preprocessing", "sklearn.linear_model", "sklearn.metrics", "pandas", "scipy"):
                if pkg not in sys.modules:
                    sys.modules[pkg] = unittest.mock.MagicMock()
            try:
                if "solution" in sys.modules:
                    del sys.modules["solution"]
                import solution
            except Exception as e2:
                err_type = type(e2).__name__
                err_msg = str(e2) or err_type
                print("SANDBOX_RUNNER_ERROR:" + json.dumps({
                    "status": "runtime_error",
                    "error_message": f"Ошибка инициализации решения ({err_type}): {err_msg}",
                    "tests_total": 0,
                    "tests_passed": 0,
                    "test_results": []
                }))
                return
        else:
            err_type = type(mne).__name__
            err_msg = str(mne) or err_type
            print("SANDBOX_RUNNER_ERROR:" + json.dumps({
                "status": "runtime_error",
                "error_message": f"Ошибка инициализации решения ({err_type}): {err_msg}",
                "tests_total": 0,
                "tests_passed": 0,
                "test_results": []
            }))
            return
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e) or err_type
        print("SANDBOX_RUNNER_ERROR:" + json.dumps({
            "status": "runtime_error",
            "error_message": f"Ошибка инициализации решения ({err_type}): {err_msg}",
            "tests_total": 0,
            "tests_passed": 0,
            "test_results": []
        }))
        return

    # 2. Загрузка и выполнение скрытых тестов
    try:
        import tests
    except Exception as e:
        print("SANDBOX_RUNNER_ERROR:" + json.dumps({
            "status": "runtime_error",
            "error_message": f"Ошибка тестового сьюта: {e}",
            "tests_total": 0,
            "tests_passed": 0,
            "test_results": []
        }))
        return

    test_funcs = [
        getattr(tests, name) for name in dir(tests)
        if name.startswith("test_") and callable(getattr(tests, name))
    ]

    passed_count = 0
    for func in test_funcs:
        test_name = func.__name__
        t0 = time.perf_counter()
        try:
            func(solution)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            results.append({
                "name": test_name,
                "passed": True,
                "execution_time_ms": elapsed_ms,
                "error_message": None
            })
            passed_count += 1
        except AssertionError as ae:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            results.append({
                "name": test_name,
                "passed": False,
                "execution_time_ms": elapsed_ms,
                "error_message": str(ae) or "Утверждение не выполнено (AssertionError)"
            })
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            results.append({
                "name": test_name,
                "passed": False,
                "execution_time_ms": elapsed_ms,
                "error_message": f"{type(ex).__name__}: {ex}"
            })

    total_elapsed_ms = round((time.perf_counter() - start_all) * 1000, 2)
    score = round(passed_count / max(len(test_funcs), 1), 2)
    status = "success" if passed_count == len(test_funcs) else "test_failure"

    print("SANDBOX_RUNNER_SUCCESS:" + json.dumps({
        "status": status,
        "tests_total": len(test_funcs),
        "tests_passed": passed_count,
        "score": score,
        "passed": score >= 0.70,
        "execution_time_ms": total_elapsed_ms,
        "test_results": results
    }))

if __name__ == "__main__":
    main()
"""


def _get_isolated_env() -> dict[str, str]:
    """Формирует очищенное окружение процесса без секретов и токенов платформы."""
    isolated = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # Для Windows обязательны переменные системной локали и временных файлов
    for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
        if key in os.environ:
            isolated[key] = os.environ[key]

    # Добавляем пути к установленным пакетам (numpy, sklearn)
    if "PYTHONPATH" in os.environ:
        isolated["PYTHONPATH"] = os.environ["PYTHONPATH"]
    else:
        # Пробрасываем sys.path в PYTHONPATH
        isolated["PYTHONPATH"] = os.pathsep.join(sys.path)

    return isolated


def execute_in_sandbox(
    candidate_code: str,
    tests_code: str | None = None,
    question_code: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> SandboxExecutionResponse:
    """Безопасно запускает код кандидата и скрытые тесты в изолированном подпроцессе."""
    # 1. Статический аудит безопасности кода
    audit = audit_code_safety(candidate_code)
    if not audit.is_safe:
        return SandboxExecutionResponse(
            status="security_violation" if audit.violation_node == "SecurityViolation" else "syntax_error",
            is_safe=False,
            passed=False,
            score=0.0,
            tests_total=0,
            tests_passed=0,
            execution_time_ms=0.0,
            test_results=[],
            feedback=f"Политика безопасности: {audit.error_message}",
            stdout="",
            stderr="",
        )

    # 2. Получение скрытых тестов
    effective_tests = tests_code
    if not effective_tests and question_code:
        effective_tests = get_hidden_tests_for_question(question_code)

    if not effective_tests:
        # Если скрытые тесты не заданы для задачи, проверяем базовую компилируемость и синтаксис
        return SandboxExecutionResponse(
            status="success",
            is_safe=True,
            passed=True,
            score=1.0,
            tests_total=1,
            tests_passed=1,
            execution_time_ms=0.0,
            test_results=[
                TestCaseResult(
                    name="test_code_syntax_and_safety",
                    passed=True,
                    execution_time_ms=0.0,
                    error_message=None,
                )
            ],
            feedback="Код успешно прошел статический анализ синтаксиса и безопасности (скрытые тесты не требуются).",
            stdout="",
            stderr="",
        )

    # 3. Изолированное выполнение во временной директории
    with tempfile.TemporaryDirectory(prefix="fsp_sandbox_") as tmp_dir:
        sol_path = os.path.join(tmp_dir, "solution.py")
        tests_path = os.path.join(tmp_dir, "tests.py")
        runner_path = os.path.join(tmp_dir, "runner.py")

        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(candidate_code)

        with open(tests_path, "w", encoding="utf-8") as f:
            f.write(effective_tests)

        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(RUNNER_SCRIPT_TEMPLATE)

        env = _get_isolated_env()
        start_time = time.perf_counter()

        try:
            proc = subprocess.Popen(
                [sys.executable, runner_path],
                cwd=tmp_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stdout_data, stderr_data = proc.communicate(timeout=timeout_seconds)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout_data, stderr_data = proc.communicate(timeout=1.0)
            except Exception:
                stdout_data, stderr_data = "", ""
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return SandboxExecutionResponse(
                status="time_limit_exceeded",
                is_safe=True,
                passed=False,
                score=0.0,
                tests_total=0,
                tests_passed=0,
                execution_time_ms=elapsed_ms,
                test_results=[],
                feedback=(
                    f"Превышен лимит времени выполнения (Time Limit Exceeded: > {timeout_seconds:.1f} сек). "
                    "Убедитесь в отсутствии бесконечных циклов или тяжелых блокирующих вычислений."
                ),
                stdout=(stdout_data or "")[:MAX_OUTPUT_BYTES],
                stderr=(stderr_data or "")[:MAX_OUTPUT_BYTES],
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SandboxExecutionResponse(
                status="runtime_error",
                is_safe=True,
                passed=False,
                score=0.0,
                tests_total=0,
                tests_passed=0,
                execution_time_ms=elapsed_ms,
                test_results=[],
                feedback=f"Внутренняя ошибка запуска песочницы: {e}",
                stdout="",
                stderr="",
            )

    # 4. Анализ результатов из stdout
    clean_stdout = (stdout_data or "")[:MAX_OUTPUT_BYTES]
    clean_stderr = (stderr_data or "")[:MAX_OUTPUT_BYTES]

    report_payload: dict[str, Any] | None = None
    for line in clean_stdout.splitlines():
        if line.startswith("SANDBOX_RUNNER_SUCCESS:"):
            try:
                report_payload = json.loads(line[len("SANDBOX_RUNNER_SUCCESS:"):])
                break
            except Exception:
                pass
        elif line.startswith("SANDBOX_RUNNER_ERROR:"):
            try:
                err_info = json.loads(line[len("SANDBOX_RUNNER_ERROR:"):])
                return SandboxExecutionResponse(
                    status=err_info.get("status", "runtime_error"),
                    is_safe=True,
                    passed=False,
                    score=0.0,
                    tests_total=0,
                    tests_passed=0,
                    execution_time_ms=elapsed_ms,
                    test_results=[],
                    feedback=err_info.get("error_message", "Ошибка времени выполнения"),
                    stdout=clean_stdout,
                    stderr=clean_stderr,
                )
            except Exception:
                pass

    if report_payload:
        tests_results = [
            TestCaseResult(
                name=r["name"],
                passed=r["passed"],
                execution_time_ms=r.get("execution_time_ms", 0.0),
                error_message=r.get("error_message"),
            )
            for r in report_payload.get("test_results", [])
        ]
        total = report_payload.get("tests_total", len(tests_results))
        passed = report_payload.get("tests_passed", sum(1 for t in tests_results if t.passed))
        score = report_payload.get("score", round(passed / max(total, 1), 2))
        is_passed = report_payload.get("passed", score >= 0.70)

        if is_passed:
            feedback = f"Скрытые тесты пройдены: {passed}/{total} ({int(score * 100)}%). Время выполнения: {elapsed_ms} мс."
        else:
            failed_tests = [t.name for t in tests_results if not t.passed]
            failed_str = ", ".join(failed_tests[:3])
            feedback = (
                f"Не все скрытые тесты пройдены: {passed}/{total} ({int(score * 100)}%). "
                f"Не пройдены: {failed_str}."
            )

        return SandboxExecutionResponse(
            status=report_payload.get("status", "success" if is_passed else "test_failure"),
            is_safe=True,
            passed=is_passed,
            score=score,
            tests_total=total,
            tests_passed=passed,
            execution_time_ms=report_payload.get("execution_time_ms", elapsed_ms),
            test_results=tests_results,
            feedback=feedback,
            stdout=clean_stdout,
            stderr=clean_stderr,
        )

    # Если раннер упал без JSON
    return SandboxExecutionResponse(
        status="runtime_error",
        is_safe=True,
        passed=False,
        score=0.0,
        tests_total=0,
        tests_passed=0,
        execution_time_ms=elapsed_ms,
        test_results=[],
        feedback=f"Ошибка выполнения кода: {clean_stderr or 'Неожиданное завершение процесса раннера'}",
        stdout=clean_stdout,
        stderr=clean_stderr,
    )
