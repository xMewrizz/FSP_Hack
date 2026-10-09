"""Пакет безопасной проверки задач с кодом (Task B-25)."""

from app.core.code_sandbox.executor import execute_in_sandbox
from app.core.code_sandbox.hidden_tests import (
    HIDDEN_TEST_SUITES,
    get_hidden_tests_for_question,
)
from app.core.code_sandbox.schemas import (
    SandboxExecutionRequest,
    SandboxExecutionResponse,
    TestCaseResult,
)
from app.core.code_sandbox.security import audit_code_safety

__all__ = [
    "audit_code_safety",
    "execute_in_sandbox",
    "get_hidden_tests_for_question",
    "HIDDEN_TEST_SUITES",
    "SandboxExecutionRequest",
    "SandboxExecutionResponse",
    "TestCaseResult",
]
