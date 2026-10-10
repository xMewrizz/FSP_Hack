"""Прототип проверки кода. Недоступен для пользовательских запросов до изоляции."""

from app.core.code_sandbox.schemas import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
)
from app.core.open_question_bank import get_open_question_by_code


class CodeSandboxService:
    @staticmethod
    def execute(request: SandboxExecutionRequest) -> SandboxExecutionResponse:
        raise RuntimeError("Запуск пользовательского кода требует отдельного изолированного исполнителя")

    @staticmethod
    def evaluate_question_code(
        question_code: str,
        candidate_code: str,
        timeout_seconds: float = 3.0,
    ) -> SandboxExecutionResponse:
        """Выполняет проверку решения задачи из банка открытых вопросов со скрытыми тестами."""
        question = get_open_question_by_code(question_code)
        if not question:
            raise ValueError(f"Вопрос с кодом {question_code} не найден")

        raise RuntimeError("Запуск пользовательского кода требует отдельного изолированного исполнителя")


code_sandbox_service = CodeSandboxService()
