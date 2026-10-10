"""Отправка кода в отдельный исполнитель; backend сам код не запускает."""

import os

import httpx

from app.core.code_sandbox.schemas import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
)
from app.core.open_question_bank import get_open_question_by_code


class UnsupportedSandboxQuestion(ValueError):
    pass


class CodeSandboxService:
    @staticmethod
    async def execute(request: SandboxExecutionRequest) -> SandboxExecutionResponse:
        if not request.question_code:
            raise ValueError("Нужно выбрать задание с закрытыми тестами")
        url = os.getenv("SANDBOX_SERVICE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("Изолированный исполнитель не настроен")
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds + 12) as client:
                response = await client.post(f"{url}/execute", json=request.model_dump())
                if response.status_code == 400:
                    raise UnsupportedSandboxQuestion("Для этого задания проверка кода пока недоступна")
                response.raise_for_status()
                result = SandboxExecutionResponse.model_validate(response.json())
                # Названия проверок и вывод процесса могут раскрыть закрытые тесты.
                # Кандидату достаточно общего результата пробного запуска.
                if result.status == "security_violation":
                    feedback = "Код не прошёл проверку допустимых операций"
                elif result.status == "time_limit_exceeded":
                    feedback = "Превышено время выполнения"
                elif result.status == "runtime_error":
                    feedback = "Код завершился с ошибкой"
                else:
                    feedback = f"Пройдено проверок: {result.tests_passed}/{result.tests_total}"
                return result.model_copy(update={
                    "test_results": [],
                    "stdout": "",
                    "stderr": "",
                    "feedback": feedback,
                })
        except UnsupportedSandboxQuestion:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("Изолированный исполнитель недоступен") from exc

    @staticmethod
    async def evaluate_question_code(
        question_code: str,
        candidate_code: str,
        timeout_seconds: float = 3.0,
    ) -> SandboxExecutionResponse:
        """Выполняет проверку решения задачи из банка открытых вопросов со скрытыми тестами."""
        question = get_open_question_by_code(question_code)
        if not question:
            raise ValueError(f"Вопрос с кодом {question_code} не найден")

        return await CodeSandboxService.execute(SandboxExecutionRequest(
            code=candidate_code,
            question_code=question_code,
            timeout_seconds=timeout_seconds,
        ))


code_sandbox_service = CodeSandboxService()
