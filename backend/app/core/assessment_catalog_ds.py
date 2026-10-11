"""Обязательные навыки и вопросы базового набора Data Science / ML."""

from app.core.question_bank_ds import DS_FAMILIES


DS_REQUIRED_SKILLS: tuple[tuple[str, str], ...] = (
    ("ds_python", "Python"),
    ("ds_pandas", "Pandas"),
    ("ds_sql", "SQL"),
    ("ds_statistics", "Вероятность и статистика"),
    ("ds_ab", "A/B-тестирование"),
    ("ds_ml", "Машинное обучение"),
)

# Названия навыков работодателя соотносятся с тестами только внутри Data Science.
# Например, Python здесь не означает тест Python для Backend.
DS_MATCHING_SKILL_CODES = {
    "python": "ds_python",
    "python для data science": "ds_python",
    "pandas": "ds_pandas",
    "sql": "ds_sql",
    "вероятность и статистика": "ds_statistics",
    "статистика": "ds_statistics",
    "a/b-тестирование": "ds_ab",
    "a/b-тесты": "ds_ab",
    "machine learning": "ds_ml",
    "машинное обучение": "ds_ml",
    "ml": "ds_ml",
    "git": "git",
    "docker": "docker",
    "подготовка данных": "data_preparation",
    "оценка моделей": "model_evaluation",
    "развёртывание моделей": "model_deployment",
    "развертывание моделей": "model_deployment",
    "анализ данных": "data_analysis",
}

DS_TARGET_QUESTIONS = {
    "ds_python": 10,
    "ds_pandas": 10,
    "ds_sql": 10,
    "ds_statistics": 10,
    "ds_ab": 10,
    "ds_ml": 10,
}


DS_QUESTION_CODES: dict[str, dict[str, tuple[str, ...]]] = {
    grade: {
        skill: tuple(sorted(
            code for code, family in DS_FAMILIES.items()
            if code.split("-")[1] == tag and family["skill_code"] == skill
        ))
        for skill, _ in DS_REQUIRED_SKILLS
    }
    for grade, tag in (("junior", "JR"), ("middle", "MID"), ("senior", "SR"))
}


def validate_ds_question_mapping() -> None:
    seen: set[str] = set()
    for grade, groups in DS_QUESTION_CODES.items():
        if set(groups) != set(DS_TARGET_QUESTIONS):
            raise ValueError(f"Missing Data Science skill in {grade}")
        for skill, codes in groups.items():
            if len(codes) != DS_TARGET_QUESTIONS[skill]:
                raise ValueError(f"Incomplete Data Science bank: {grade}/{skill}")
            for code in codes:
                if code in seen or DS_FAMILIES[code]["skill_code"] != skill:
                    raise ValueError(f"Duplicated or substituted Data Science question: {code}")
                seen.add(code)


validate_ds_question_mapping()
