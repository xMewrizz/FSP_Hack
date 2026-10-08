"""Единый справочник специализаций и грейдов (B-01).

Канонический источник для: анкеты кандидата, потребности работодателя,
фильтров банка и запуска теста. Интерфейс и backend обязаны брать значения
отсюда, а не из локальных захардкоженных списков.

Правила MVP (см. docs/00-tz-keypoints.md, docs/02-testing-matching.md):
- Грейд подтверждает ТОЛЬКО тест. Достижения ФСП влияют на порядок внутри
  категории, но грейд не подтверждают и не меняют.
- Первый рабочий сценарий: специализация Backend + грейды junior/middle/senior.
- Остальные специализации и грейд lead из данных НЕ удаляются (профиль,
  потребность и фильтры их знают), но как доступные для прохождения теста
  не показываются, пока для них нет проверенного банка заданий.
- Тихая подмена вопросов запрещена: нельзя незаметно выдавать вопросы другой
  специализации или уровня. Неподдерживаемая пара -> явная ошибка со списком
  доступного.

Модуль намеренно чистый (только stdlib + app.core.constants): его можно
импортировать и тестировать без БД и моделей данных.
"""

from app.core.constants import SPECIALIZATIONS


class CatalogError(ValueError):
    """Пара «специализация + грейд» не поддерживается для запуска теста."""


# Все известные значения — для профиля, потребности и фильтров (не удалять).
ALL_SPECIALIZATIONS: list[str] = list(SPECIALIZATIONS)
ALL_GRADES: list[str] = ["junior", "middle", "senior", "lead"]

# Доступное для прохождения теста прямо сейчас (первый сценарий B-01).
# Frontend/DevOps-строки в question_bank.py существуют, но как набор для запуска
# не заявлены: проверку банка делает B-02, до неё банк проверенным не называем.
TESTABLE_SPECIALIZATIONS: list[str] = ["Backend"]
TESTABLE_GRADES: list[str] = ["junior", "middle", "senior"]

TESTABLE_PAIRS: set[tuple[str, str]] = {
    (spec, grade) for spec in TESTABLE_SPECIALIZATIONS for grade in TESTABLE_GRADES
}

# Минимум вопросов на пару, чтобы тест собирался (сейчас у Backend 4/грейд).
MIN_QUESTIONS_PER_PAIR = 3

GRADE_LABELS_RU: dict[str, str] = {
    "junior": "Junior",
    "middle": "Middle",
    "senior": "Senior",
    "lead": "Lead",
}

# Порядок грейдов для предложений следующего шага (B-12). Сам lead из данных
# не удалён, но пока пары с ним нет в TESTABLE_PAIRS — предлагать тест,
# которого нет, нельзя.


def suggest_upshift_grade(specialization: str | None, current_grade: str | None) -> str | None:
    """Следующий грейд для предложения после уверенного результата.

    Возвращает None, если пары со следующим грейдом нет в TESTABLE_PAIRS
    (например, senior -> lead, пока lead недоступен для теста): предлагать
    несуществующий тест запрещено. Чистая функция — правило 90 дней и скоринг
    здесь не затрагиваются.
    """
    order = ["junior", "middle", "senior", "lead"]
    current = normalize_grade(current_grade)
    spec = normalize_specialization(specialization)
    if not spec or not current or current not in order:
        return None
    nxt = order[order.index(current) + 1] if order.index(current) + 1 < len(order) else None
    if nxt is None:
        return None
    return nxt if is_testable(spec, nxt) else None


def available_for_test_hint() -> str:
    pairs = ", ".join(f"{s} {g}" for s, g in sorted(TESTABLE_PAIRS))
    return f"Сейчас тест доступен для: {pairs}."


def normalize_specialization(value: str | None) -> str | None:
    """Возвращает каноническое написание из ALL_SPECIALIZATIONS (регистр не важен)."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    for canonical in ALL_SPECIALIZATIONS:
        if canonical.lower() == cleaned.lower():
            return canonical
    return cleaned  # неизвестное — вернуть как есть, проверку делает validate_test_pair


def normalize_grade(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def is_testable(specialization: str | None, grade: str | None) -> bool:
    spec = normalize_specialization(specialization)
    grd = normalize_grade(grade)
    return (spec, grd) in TESTABLE_PAIRS if spec and grd else False


def validate_test_pair(specialization: str | None, grade: str | None) -> tuple[str, str]:
    """Проверяет пару для запуска теста. Кидает CatalogError с ясным текстом."""
    spec = normalize_specialization(specialization)
    grd = normalize_grade(grade)
    if not spec or not grd:
        raise CatalogError(
            "Не указаны специализация и грейд для теста. " + available_for_test_hint()
        )
    if (spec, grd) not in TESTABLE_PAIRS:
        raise CatalogError(
            f"Тест для пары «{spec} / {grd}» пока недоступен: задания первого сценария "
            "подготовлены только для Backend junior/middle/senior. "
            + available_for_test_hint()
            + " Вопросы другой специализации или уровня не подставляются."
        )
    return spec, grd


def assert_no_substitution(
    specialization: str, grade: str, questions: list[object]
) -> None:
    """Защита от подмены: все выданные вопросы обязаны совпадать с парой.

    `questions` — объекты Question (БД) либо словари банка с ключами
    specialization/grade. Любое расхождение -> CatalogError, а не тихий фолбэк.
    """

    def _pair_of(q: object) -> tuple[str | None, str | None]:
        if isinstance(q, dict):
            return q.get("specialization"), q.get("grade")
        return getattr(q, "specialization", None), getattr(q, "grade", None)

    for q in questions:
        q_spec, q_grade = _pair_of(q)
        if q_spec != specialization or q_grade != grade:
            code = q.get("code") if isinstance(q, dict) else getattr(q, "code", "?")
            raise CatalogError(
                f"Обнаружена подмена вопросов: запрошено «{specialization} / {grade}», "
                f"а вопрос {code} относится к «{q_spec} / {q_grade}». "
                "Выдача остановлена."
            )


def catalog_coverage(question_bank: list[dict]) -> dict[tuple[str, str], int]:
    """Сколько вопросов банка приходится на каждую пару (для проверки B-02)."""
    coverage: dict[tuple[str, str], int] = {}
    for q in question_bank:
        key = (q.get("specialization"), q.get("grade"))
        coverage[key] = coverage.get(key, 0) + 1
    return coverage
