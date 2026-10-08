"""Правила итоговой оценки набора обязательных навыков.

Модуль не зависит от БД: результат одного навыка может приходить из теста с
выбором ответа, задачи с кодом или проверенного открытого ответа.
"""

from dataclasses import dataclass


OVERALL_MINIMUM = 0.75
SKILL_MINIMUM = 0.50


@dataclass(frozen=True)
class SkillResult:
    code: str
    earned: float
    maximum: float

    def __post_init__(self) -> None:
        if self.maximum <= 0 or self.earned < 0 or self.earned > self.maximum:
            raise ValueError(f"Некорректные баллы навыка {self.code}")

    @property
    def ratio(self) -> float:
        return self.earned / self.maximum

    @property
    def level_out_of_ten(self) -> float:
        """Показатель относительно проверяемого грейда, а не абсолютная оценка."""
        return round(10 * self.ratio, 1)


@dataclass(frozen=True)
class GradeDecision:
    complete: bool
    passed: bool
    overall_ratio: float | None
    missing_skills: tuple[str, ...]
    below_minimum: tuple[str, ...]


def assess_grade(
    required_skills: tuple[str, ...],
    results: list[SkillResult],
    *,
    overall_minimum: float = OVERALL_MINIMUM,
    skill_minimum: float = SKILL_MINIMUM,
) -> GradeDecision:
    """Оценить только обязательные навыки одного грейда и специализации.

    Дополнительные навыки сюда не передаются. Порог сравнивается с точным
    отношением баллов: округление для интерфейса не меняет решение.
    """
    if not required_skills or len(required_skills) != len(set(required_skills)):
        raise ValueError("Набор обязательных навыков пуст или содержит повторы")
    if not 0 <= overall_minimum <= 1 or not 0 <= skill_minimum <= 1:
        raise ValueError("Порог должен быть долей от 0 до 1")
    by_code = {result.code: result for result in results}
    if len(by_code) != len(results):
        raise ValueError("Для одного навыка передано несколько результатов")
    unknown = set(by_code) - set(required_skills)
    if unknown:
        raise ValueError(f"Посторонние навыки в наборе: {', '.join(sorted(unknown))}")

    missing = tuple(code for code in required_skills if code not in by_code)
    if missing:
        return GradeDecision(False, False, None, missing, ())

    if len({result.maximum for result in results}) != 1:
        raise ValueError("Обязательные навыки должны иметь одинаковый максимум баллов")

    earned = sum(result.earned for result in results)
    maximum = sum(result.maximum for result in results)
    overall = earned / maximum
    below = tuple(code for code in required_skills if by_code[code].ratio < skill_minimum)
    return GradeDecision(True, overall >= overall_minimum and not below, overall, (), below)
