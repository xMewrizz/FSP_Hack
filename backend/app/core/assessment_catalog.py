"""Обязательные навыки Backend и фактическое покрытие банка заданий.

Навык имеет один код на всех грейдах. Пустой набор кодов означает, что тест
по этой паре пока не готов; подставлять вопросы другого навыка нельзя.
"""

from app.core.question_bank import PREDEFINED_QUESTIONS
from app.core.assessment_catalog_ds import DS_REQUIRED_SKILLS


BACKEND_REQUIRED_SKILLS: tuple[tuple[str, str], ...] = (
    ("backend_python", "Python для Backend"),
    ("sql", "SQL и работа с данными"),
    ("api", "HTTP API и интеграция"),
    ("reliability", "Надёжность сервиса"),
)
TARGET_QUESTIONS_PER_REQUIRED_SKILL = 10

SKILL_LABELS = {
    **dict(BACKEND_REQUIRED_SKILLS),
    **dict(DS_REQUIRED_SKILLS),
    "git": "Git и контроль версий",
}

# Только точные названия тем тестов. FastAPI, PostgreSQL и другие технологии
# нельзя приравнивать к более широким тестам по API или SQL.
BACKEND_MATCHING_SKILL_CODES = {
    "python": "backend_python",
    "python для backend": "backend_python",
    "sql": "sql",
    "sql и работа с данными": "sql",
    "http api": "api",
    "http api и интеграция": "api",
    "надёжность сервиса": "reliability",
    "надежность сервиса": "reliability",
    "git": "git",
    "git и контроль версий": "git",
}

BACKEND_QUESTION_CODES: dict[str, dict[str, tuple[str, ...]]] = {
    "junior": {
        "backend_python": ("BE-JR-02", "BE-JR-07", "BE-JR-08", *(f"BE-JR-{n}" for n in range(16, 23))),
        "sql": ("BE-JR-01", "BE-JR-05", "BE-JR-06", *(f"BE-JR-{n}" for n in range(23, 30))),
        "api": ("BE-JR-03", "BE-JR-09", "BE-JR-10", *(f"BE-JR-{n}" for n in range(30, 37))),
        "reliability": ("BE-JR-13", "BE-JR-14", "BE-JR-15", *(f"BE-JR-{n}" for n in range(37, 44))),
    },
    "middle": {
        "backend_python": ("BE-MID-01", "BE-MID-05", "BE-MID-06", *(f"BE-MID-{n}" for n in range(16, 23))),
        "sql": ("BE-MID-02", "BE-MID-07", "BE-MID-08", *(f"BE-MID-{n}" for n in range(23, 30))),
        "api": ("BE-MID-13", "BE-MID-14", "BE-MID-15", *(f"BE-MID-{n}" for n in range(30, 37))),
        "reliability": ("BE-MID-03", "BE-MID-09", "BE-MID-10", *(f"BE-MID-{n}" for n in range(37, 44))),
    },
    "senior": {
        "backend_python": ("BE-SR-13", "BE-SR-14", "BE-SR-15", *(f"BE-SR-{n}" for n in range(19, 26))),
        "sql": ("BE-SR-16", "BE-SR-17", "BE-SR-18", *(f"BE-SR-{n}" for n in range(26, 33))),
        "api": ("BE-SR-01", "BE-SR-05", "BE-SR-06", *(f"BE-SR-{n}" for n in range(33, 40))),
        "reliability": ("BE-SR-03", "BE-SR-09", "BE-SR-10", *(f"BE-SR-{n}" for n in range(40, 47))),
    },
}

# Каталог тестов привязан к навыку и сложности. Специализация только выбирает,
# какие навыки обязательны: одни и те же коды можно использовать в другом наборе.
SKILL_QUESTION_CODES: dict[str, dict[str, tuple[str, ...]]] = {
    grade: dict(groups) for grade, groups in BACKEND_QUESTION_CODES.items()
}
SKILL_QUESTION_CODES["junior"]["git"] = (
    "BE-JR-04", "BE-JR-11", "BE-JR-12",
)


def available_extra_skills(specialization: str) -> list[tuple[str, str, str]]:
    if specialization != "Backend":
        return []
    required = {code for code, _ in BACKEND_REQUIRED_SKILLS}
    return [
        (code, SKILL_LABELS[code], grade)
        for grade, groups in SKILL_QUESTION_CODES.items()
        for code, codes in groups.items()
        if code not in required and len(codes) >= 3
    ]


def backend_curriculum_gaps() -> list[tuple[str, str, int]]:
    """Сколько самостоятельных заданий нужно до согласованного минимума."""
    return [
        (grade, code, TARGET_QUESTIONS_PER_REQUIRED_SKILL - len(question_codes))
        for grade, groups in BACKEND_QUESTION_CODES.items()
        for code, question_codes in groups.items()
        if len(question_codes) < TARGET_QUESTIONS_PER_REQUIRED_SKILL
    ]


def validate_backend_question_mapping() -> None:
    """Проверить, что подготовленные вопросы не подменены другой парой."""
    questions = {question["code"]: question for question in PREDEFINED_QUESTIONS}
    required_codes = {code for code, _ in BACKEND_REQUIRED_SKILLS}
    for grade, groups in BACKEND_QUESTION_CODES.items():
        if set(groups) != required_codes:
            raise ValueError(f"Неполный список навыков Backend {grade}")
        if len({len(codes) for codes in groups.values()}) != 1:
            raise ValueError(f"Неравное число заданий обязательных навыков для {grade}")
        seen: set[str] = set()
        for skill_code, codes in groups.items():
            if not codes:
                raise ValueError(f"Нет заданий для {grade} / {skill_code}")
            for code in codes:
                if code in seen:
                    raise ValueError(f"Вопрос {code} включён в два обязательных навыка")
                seen.add(code)
                question = questions.get(code)
                if question is None or question["specialization"] != "Backend" or question["grade"] != grade:
                    raise ValueError(f"Вопрос {code} не соответствует Backend {grade}")
