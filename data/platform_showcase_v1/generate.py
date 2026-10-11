"""Синтетические профили, вакансии и задания для шести пар специализация × грейд.

Запуск из корня репозитория:
    python data/platform_showcase_v1/generate.py
"""

from __future__ import annotations

import json
from pathlib import Path


OUT = Path(__file__).resolve().parent
SEED_NOTE = "Вымышленные профили. Не связаны с реальными людьми и компаниями."

PAIRS = [
    ("Backend", "junior"),
    ("Backend", "middle"),
    ("Backend", "senior"),
    ("Data Science / ML", "junior"),
    ("Data Science / ML", "middle"),
    ("Data Science / ML", "senior"),
]

REQUIRED = {
    "Backend": [
        ("backend_python", "Python для Backend"),
        ("sql", "SQL и работа с данными"),
        ("api", "HTTP API и интеграция"),
        ("reliability", "Надёжность сервиса"),
    ],
    "Data Science / ML": [
        ("ds_python", "Python"),
        ("ds_pandas", "Pandas"),
        ("ds_sql", "SQL"),
        ("ds_statistics", "Вероятность и статистика"),
        ("ds_ab", "A/B-тестирование"),
        ("ds_ml", "Машинное обучение"),
    ],
}

EXTRA = {
    "Backend": [
        ("git", "Git"),
        ("docker", "Docker"),
        ("redis", "Redis и кэширование"),
    ],
    "Data Science / ML": [
        ("git", "Git"),
        ("docker", "Docker"),
        ("data_preparation", "Подготовка данных"),
        ("model_evaluation", "Оценка моделей"),
        ("model_deployment", "Развёртывание моделей"),
        ("data_analysis", "Анализ данных"),
    ],
}

NAMES = [
    ("Алина", "Орлова"), ("Борис", "Соколов"), ("Вера", "Белова"), ("Глеб", "Крылов"),
    ("Дина", "Морозова"), ("Егор", "Волков"), ("Жанна", "Лебедева"), ("Захар", "Новиков"),
    ("Ирина", "Павлова"), ("Кирилл", "Фомин"), ("Лариса", "Егорова"), ("Максим", "Калинин"),
    ("Нина", "Никитина"), ("Олег", "Зайцев"), ("Полина", "Комарова"), ("Руслан", "Белов"),
    ("Софья", "Сафонова"), ("Тимур", "Громов"), ("Ульяна", "Тихонова"), ("Фёдор", "Ершов"),
    ("Элина", "Баранова"), ("Юрий", "Кузьмин"), ("Яна", "Данилова"), ("Артём", "Серов"),
    ("Валерия", "Жукова"), ("Григорий", "Макаров"), ("Дарья", "Филатова"), ("Илья", "Осипов"),
    ("Ксения", "Чернова"), ("Лев", "Виноградов"), ("Марина", "Киселёва"), ("Назар", "Рогов"),
    ("Ольга", "Семёнова"), ("Пётр", "Андреев"), ("Регина", "Котова"), ("Степан", "Медведев"),
    ("Тамара", "Субботина"), ("Антон", "Власов"), ("Варвара", "Демина"), ("Денис", "Капустин"),
    ("Ева", "Логинова"), ("Игорь", "Мартынов"), ("Карина", "Нестерова"), ("Леонид", "Орлов"),
    ("Мила", "Петрова"), ("Никита", "Рыбаков"), ("Оксана", "Савельева"), ("Павел", "Тарасов"),
    ("Раиса", "Уварова"), ("Сергей", "Фролов"), ("Татьяна", "Харитонова"), ("Эдуард", "Цветков"),
    ("Юлия", "Шубина"), ("Яков", "Щербаков"), ("Агата", "Юдина"), ("Вадим", "Яковлев"),
    ("Галина", "Абрамова"), ("Дмитрий", "Быков"), ("Елена", "Воронова"), ("Зоя", "Гусева"),
]
CITIES = ["Москва", "Казань", "Новосибирск", "Екатеринбург", "Томск", "Самара", "Пермь", "Воронеж"]
FORMATS = ["remote", "hybrid", "office"]

COMPANIES = [
    ("northline", "Нордлайн", "Финтех", "Москва"),
    ("vectorlab", "Векторлаб", "Аналитика", "Казань"),
    ("harbor", "Харбор", "Логистика", "Санкт-Петербург"),
    ("lumen", "Люмен", "Медиа", "Новосибирск"),
    ("kiln", "Килн", "Промышленный софт", "Екатеринбург"),
    ("papertrail", "Пейпертрейл", "Документооборот", "Самара"),
    ("fieldnote", "Филдноут", "Исследования", "Томск"),
    ("relay", "Релей", "Коммуникации", "Пермь"),
]

TOURNAMENTS = [
    ("Открытый кубок алгоритмов", "финалист"),
    ("Весенний контест ФСП", "дипломант"),
    ("Осенний турнир", "призёр"),
    ("Командный хакатон ФСП", "участник финала"),
]


def percentage(pair_index: int, person: int, skill_index: int) -> int:
    # Ten choice questions give scores in steps of ten. Confirmed profiles
    # satisfy the actual policy: >=75% overall and >=50% for every skill.
    if person == 4:
        return 40 if skill_index == 0 else 50 + 10 * ((pair_index + skill_index) % 3)
    return 70 + 10 * ((pair_index + person + skill_index) % 4)


def completeness(profile: dict) -> dict:
    def filled(value: object) -> bool:
        return bool(isinstance(value, str) and value.strip())

    checks = [
        ("имя и фамилию", 5, filled(profile["first_name"]) and filled(profile["last_name"])),
        ("подтверждение email", 20, profile["email_verified"]),
        ("номер телефона", 30, filled(profile["phone"])),
        (
            "специализацию, язык и заявленный грейд", 5,
            filled(profile["specialization"]) and filled(profile["programming_language"]) and filled(profile["declared_grade"]),
        ),
        (
            "город, формат и ожидания по зарплате", 5,
            filled(profile["city"]) and filled(profile["work_format"]) and profile["salary_expectation"] is not None,
        ),
        ("навыки", 5, bool(profile["skills"])),
        ("прикреплённое резюме", 10, filled(profile["resume_url"])),
        ("подтверждение грейда тестом", 20, filled(profile["verified_grade"])),
    ]
    score = sum(points for _, points, done in checks if done)
    status = "insufficient" if score < 40 else "partial" if score < 100 else "complete"
    return {"score": score, "status": status, "missing": [label for label, _, done in checks if not done]}


def build_candidates() -> list[dict]:
    people = []
    number = 0
    for pair_index, (specialization, grade) in enumerate(PAIRS):
        for person in range(10):
            number += 1
            first, last = NAMES[number - 1]
            verified = person not in {4, 7}
            has_fsp = person in {0, 1, 3, 5, 8}
            mentor = person in {0, 2, 6, 8} and verified
            email_verified = person not in {4, 7}
            phone = None if person in {2, 7} else f"+7 900 {100 + number:03d}-{10 + person:02d}-{20 + pair_index:02d}"
            city = None if person in {5, 7} else CITIES[(number + person) % len(CITIES)]
            salary = None if person in {5, 7} else 80000 + grade_salary(grade) + person * 7000
            skills = [] if person == 7 else [label for _, label in REQUIRED[specialization][: 2 + person % 3]]
            resume_url = None if person in {3, 4, 7} else f"https://files.example/resume/{number}.pdf"
            bio = None if person in {4, 6, 7} else f"Ищу задачи уровня {grade} в направлении {specialization}."
            github = None if person in {6, 7, 9} else f"https://github.com/example-{number}"
            hobbies = None if person % 3 else "Шахматы и настольные игры"
            required_results = [
                {
                    "code": code,
                    "label": label,
                    "kind": "required",
                    "percentage": percentage(pair_index, person, index) if verified or person != 7 else None,
                    "correct": None,
                    "total": 10,
                }
                for index, (code, label) in enumerate(REQUIRED[specialization])
            ]
            for item in required_results:
                if item["percentage"] is not None:
                    item["correct"] = round(item["percentage"] / 10)
            extra_pool = EXTRA[specialization]
            extra_count = 0 if person % 3 == 2 else 1 if person % 3 == 1 else 2
            additional = []
            for offset in range(extra_count):
                code, label = extra_pool[(person + offset) % len(extra_pool)]
                score = 60 + 20 * ((person + offset) % 3)
                additional.append({
                    "code": code,
                    "label": label,
                    "kind": "additional",
                    "percentage": score,
                    "correct": round(score / 20),
                    "total": 5,
                })
            achievement = None
            if has_fsp:
                tournament, place = TOURNAMENTS[number % len(TOURNAMENTS)]
                achievement = {
                    "tournament_name": tournament,
                    "year": 2023 + (number % 3),
                    "rank_or_place": place,
                    "sport_category": "кандидат в мастера" if grade == "senior" else "первый разряд",
                    "score_or_rating": 1800 + number * 7,
                    "is_demo": True,
                }
            profile = {
                "id": f"cand-{number:03d}",
                "email": f"candidate{number:03d}@example.test",
                "email_verified": email_verified,
                "first_name": first,
                "last_name": last,
                "phone": phone,
                "telegram": None if person % 4 == 0 else f"@candidate{number:03d}",
                "city": city,
                "bio": bio,
                "hobbies": hobbies,
                "github_url": github,
                "resume_url": resume_url,
                "specialization": specialization,
                "programming_language": "Python",
                "declared_grade": grade,
                "verified_grade": grade if verified else None,
                "work_format": None if person == 7 else FORMATS[person % len(FORMATS)],
                "salary_expectation": salary,
                "salary_tax_type": "net" if person % 2 else "gross",
                "skills": skills,
                "mentor_available": mentor,
                "visibility_public": person not in {4, 7},
                "onboarding_completed": person != 7,
                "fsp_id": f"FSP-DEMO-{number:03d}" if has_fsp else None,
                "fsp_verified": has_fsp,
                "fsp_achievement": achievement,
                "required_test_results": required_results,
                "additional_test_results": additional,
            }
            profile["profile_completeness"] = completeness(profile)
            people.append(profile)
    return people


def grade_salary(grade: str) -> int:
    return {"junior": 0, "middle": 70000, "senior": 150000}[grade]


def build_companies() -> list[dict]:
    return [
        {
            "id": code,
            "company_name": name,
            "industry": industry,
            "city": city,
            "website": f"https://{code}.example",
            "contact_person": "Отдел найма",
        }
        for code, name, industry, city in COMPANIES
    ]


def build_vacancies() -> list[dict]:
    counts = [3, 2, 2, 3, 3, 2]
    vacancies = []
    number = 0
    for pair_index, (specialization, grade) in enumerate(PAIRS):
        for slot in range(counts[pair_index]):
            number += 1
            company = COMPANIES[(pair_index * 3 + slot) % len(COMPANIES)]
            vacancies.append({
                "id": f"vac-{number:03d}",
                "company_id": company[0],
                "company_name": company[1],
                "title": f"{specialization}, {grade}",
                "specialization": specialization,
                "required_grade": grade,
                "required_skills": [label for _, label in REQUIRED[specialization][:3]],
                "salary_min": grade_salary(grade) + 120000,
                "salary_max": grade_salary(grade) + 220000,
                "salary_tax_type": "gross" if slot % 2 == 0 else "net",
                "currency": "RUB",
                "work_format": FORMATS[slot % len(FORMATS)],
                "city": company[3] if slot % 2 else None,
                "description": f"Вакансия {grade} по направлению {specialization}. Компания {company[1]}.",
                "is_published": True,
            })
    return vacancies


TASKS = [
    (
        "Проверка входных данных API",
        "Опишите, как обработать некорректное тело запроса и какой код ответа вернуть клиенту.",
        "Вернуть 400 и сообщение о поле с ошибкой, не обрабатывая запрос дальше.",
        ["Назван код 400", "Указано конкретное поле", "Запрос не выполняется после ошибки"],
    ),
    (
        "Повтор безопасного запроса",
        "Клиент повторил GET из-за таймаута. Что должен сделать сервис?",
        "Повторно вернуть то же представление ресурса, не создавая новую сущность.",
        ["GET не создаёт ресурс", "Повтор не меняет состояние", "Ответ соответствует текущему ресурсу"],
    ),
    (
        "Идемпотентная запись",
        "Платёж с тем же ключом идемпотентности пришёл второй раз после успеха первого.",
        "Вернуть сохранённый результат первого запроса и не списывать деньги снова.",
        ["Ключ идемпотентности сохранён вместе с результатом", "Повтор не создаёт второе списание", "Ответ совпадает с первым успешным"],
    ),
    (
        "Пропуски в обучающей таблице",
        "В целевой колонке есть пустые значения. Как подготовить таблицу к обучению?",
        "Удалить строки без цели и не заполнять цель средним по всей таблице.",
        ["Строки без цели исключены", "Цель не заполняется статистикой всего набора", "Остальные колонки не удаляются без причины"],
    ),
    (
        "Утечка при масштабировании",
        "Признаки нужно стандартизировать до кросс-валидации. Где считать среднее и отклонение?",
        "Считать параметры только на обучающей части каждого разбиения и применять их к проверке.",
        ["Параметры не считаются на тесте", "Преобразование входит в разбиение", "Назван риск утечки"],
    ),
    (
        "Сдвиг данных после выката",
        "После выката скоринг стал чаще отвечать ошибкой, а качество на отложенных метках ещё неизвестно. Что проверить сначала?",
        "Сравнить распределение входных признаков и кодов ошибок с периодом до выката, затем решить, откатывать ли модель.",
        ["Сравниваются входы до и после выката", "Учитываются ошибки сервиса", "Решение об откате не ждёт всех отложенных меток"],
    ),
]


def build_tasks(vacancies: list[dict]) -> list[dict]:
    tasks = []
    for pair_index, (specialization, grade) in enumerate(PAIRS):
        title, description, reference, criteria = TASKS[pair_index]
        vacancy = next(item for item in vacancies if item["specialization"] == specialization and item["required_grade"] == grade)
        tasks.append({
            "id": f"task-{pair_index + 1:02d}",
            "company_id": vacancy["company_id"],
            "vacancy_id": vacancy["id"],
            "title": title,
            "description": description,
            "task_type": "manual_review",
            "reference_answer": reference,
            "evaluation_criteria": criteria,
            "specialization": specialization,
            "min_grade": grade,
            "max_grade": grade,
            "max_score": 10,
            "is_active": True,
        })
    return tasks


def main() -> None:
    candidates = build_candidates()
    companies = build_companies()
    vacancies = build_vacancies()
    tasks = build_tasks(vacancies)
    fsp_count = sum(person["fsp_verified"] for person in candidates)
    mentor_count = sum(person["mentor_available"] for person in candidates)
    manifest = {
        "note": SEED_NOTE,
        "pairs": [{"specialization": spec, "grade": grade} for spec, grade in PAIRS],
        "candidates": len(candidates),
        "candidates_per_pair": 10,
        "with_one_fsp_achievement": fsp_count,
        "mentor_available": mentor_count,
        "companies": len(companies),
        "vacancies": len(vacancies),
        "tasks": len(tasks),
    }
    for name, payload in (
        ("manifest.json", manifest),
        ("companies.json", companies),
        ("candidates.json", candidates),
        ("vacancies.json", vacancies),
        ("tasks.json", tasks),
    ):
        (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
