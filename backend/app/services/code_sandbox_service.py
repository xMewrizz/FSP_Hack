"""Сервис безопасного запуска и тестирования кода в песочнице (Task B-25)."""

from app.core.code_sandbox.executor import execute_in_sandbox
from app.core.code_sandbox.hidden_tests import get_hidden_tests_for_question
from app.core.code_sandbox.schemas import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
)
from app.core.open_question_bank import get_open_question_by_code


class CodeSandboxService:
    @staticmethod
    def execute(request: SandboxExecutionRequest) -> SandboxExecutionResponse:
        """Запускает код кандидата в изолированной песочнице."""
        return execute_in_sandbox(
            candidate_code=request.code,
            tests_code=request.custom_tests_code,
            question_code=request.question_code,
            timeout_seconds=request.timeout_seconds,
        )

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

        hidden_tests = get_hidden_tests_for_question(question_code)

        return execute_in_sandbox(
            candidate_code=candidate_code,
            tests_code=hidden_tests,
            question_code=question_code,
            timeout_seconds=timeout_seconds,
        )


code_sandbox_service = CodeSandboxService()
