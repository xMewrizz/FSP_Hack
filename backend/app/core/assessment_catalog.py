"""Обязательные навыки Backend и фактическое покрытие банка заданий.

Навык имеет один код на всех грейдах. Пустой набор кодов означает, что тест
по этой паре пока не готов; подставлять вопросы другого навыка нельзя.
"""

from app.core.question_bank import PREDEFINED_QUESTIONS
from app.core.assessment_catalog_ds import DS_REQUIRED_SKILLS
from app.core.additional_skill_bank import ADDITIONAL_SKILLS, available_additional_skills


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
    **{code: data["label"] for code, data in ADDITIONAL_SKILLS.items()},
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
    "docker": "docker",
    "redis": "redis",
    "redis и кэширование": "redis",
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
    return [(code, label, "all") for code, label in available_additional_skills(specialization)]


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


def get_testing_catalog() -> dict:
    """Каталог поддерживаемых специализаций, языков и тестов (B-39)."""
    return {
        "specializations": [
            {
                "specialization": "Backend",
                "is_available": True,
                "languages": [
                    {"name": "Python", "available": True, "reason": None},
                    {"name": "Go", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "Java", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "C#", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "Node.js", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": ["junior", "middle", "senior"],
                "required_skills": [
                    {"code": code, "label": label}
                    for code, label in BACKEND_REQUIRED_SKILLS
                ],
                "additional_skills": [
                    {"code": code, "label": label, "grade": grade}
                    for code, label, grade in available_extra_skills("Backend")
                ],
                "note": "Базовый тест доступен на Python для трёх грейдов. Дополнительные навыки проверяются отдельно и не зависят от грейда.",
            },
            {
                "specialization": "Data Science / ML",
                "is_available": True,
                "languages": [
                    {"name": "Python", "available": True, "reason": None},
                    {"name": "R", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": ["junior", "middle", "senior"],
                "required_skills": [
                    {"code": code, "label": label}
                    for code, label in DS_REQUIRED_SKILLS
                ],
                "additional_skills": [
                    {"code": code, "label": label, "grade": grade}
                    for code, label, grade in available_extra_skills("Data Science / ML")
                ],
                "note": "Базовый набор доступен на Python для Junior, Middle, Senior (Python, Pandas, SQL, статистика, A/B, ML).",
            },
            {
                "specialization": "Frontend",
                "is_available": False,
                "languages": [
                    {"name": "TypeScript", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "JavaScript", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": [],
                "required_skills": [],
                "additional_skills": [],
                "note": "Специализация Frontend в разработке",
            },
            {
                "specialization": "Fullstack",
                "is_available": False,
                "languages": [
                    {"name": "TypeScript / Python", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": [],
                "required_skills": [],
                "additional_skills": [],
                "note": "Специализация Fullstack в разработке",
            },
            {
                "specialization": "Mobile",
                "is_available": False,
                "languages": [
                    {"name": "Kotlin", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "Swift", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": [],
                "required_skills": [],
                "additional_skills": [],
                "note": "Специализация Mobile в разработке",
            },
            {
                "specialization": "DevOps",
                "is_available": False,
                "languages": [
                    {"name": "Python / Bash", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": [],
                "required_skills": [],
                "additional_skills": [],
                "note": "Специализация DevOps в разработке",
            },
            {
                "specialization": "QA",
                "is_available": False,
                "languages": [
                    {"name": "Python", "available": False, "reason": "Банк заданий в разработке"},
                    {"name": "Java", "available": False, "reason": "Банк заданий в разработке"},
                ],
                "available_grades": [],
                "required_skills": [],
                "additional_skills": [],
                "note": "Специализация QA в разработке",
            },
        ],
        "supported_pairs": [
            {"specialization": "Backend", "programming_language": "Python", "grade": "junior"},
            {"specialization": "Backend", "programming_language": "Python", "grade": "middle"},
            {"specialization": "Backend", "programming_language": "Python", "grade": "senior"},
            {"specialization": "Data Science / ML", "programming_language": "Python", "grade": "junior"},
            {"specialization": "Data Science / ML", "programming_language": "Python", "grade": "middle"},
            {"specialization": "Data Science / ML", "programming_language": "Python", "grade": "senior"},
        ],
    }
