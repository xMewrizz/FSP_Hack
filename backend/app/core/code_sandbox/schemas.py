"""Схемы данных для безопасной песочницы проверки кода (Task B-25)."""

from typing import Any
from pydantic import BaseModel, Field


class TestCaseResult(BaseModel):
    name: str = Field(..., description="Название тест-кейса")
    passed: bool = Field(..., description="Пройден ли тест")
    execution_time_ms: float = Field(0.0, description="Время выполнения тест-кейса в миллисекундах")
    error_message: str | None = Field(None, description="Сообщение об ошибке при падении")


class SandboxExecutionRequest(BaseModel):
    code: str = Field(..., description="Исходный код кандидата для проверки")
    question_code: str | None = Field(None, description="Код вопроса из банка, если применимо")
    custom_tests_code: str | None = Field(None, description="Пользовательский код скрытых тестов (опционально)")
    timeout_seconds: float = Field(3.0, ge=0.5, le=10.0, description="Лимит времени выполнения в секундах")


class SandboxExecutionResponse(BaseModel):
    status: str = Field(
        ...,
        description="Статус выполнения: success, test_failure, time_limit_exceeded, security_violation, syntax_error, runtime_error",
    )
    is_safe: bool = Field(..., description="Прошел ли код статический аудит безопасности")
    passed: bool = Field(..., description="Считается ли задача успешно решенной (порог >= 70%)")
    score: float = Field(0.0, ge=0.0, le=1.0, description="Балл от 0.0 до 1.0 (доля пройденных скрытых тестов)")
    tests_total: int = Field(0, description="Всего скрытых тестов")
    tests_passed: int = Field(0, description="Успешно пройдено скрытых тестов")
    execution_time_ms: float = Field(0.0, description="Общее время выполнения в миллисекундах")
    test_results: list[TestCaseResult] = Field(default_factory=list, description="Результаты по каждому тест-кейсу")
    feedback: str = Field("", description="Понятная обратная связь для кандидата и проверяющего")
    stdout: str = Field("", description="Стандартный вывод (с ограничением объема)")
    stderr: str = Field("", description="Стандартный поток ошибок (с ограничением объема)")
    evaluator: str = Field("code_sandbox_b25", description="Идентификатор оценщика")
