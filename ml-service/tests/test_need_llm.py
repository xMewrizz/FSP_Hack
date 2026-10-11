import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from need_llm import suggest_need


class NeedLlmTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_sets_distinct_skill_weights_from_tasks(self):
        def reply(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(request.url.path, "/api/chat")
            self.assertEqual(payload["model"], "qwen3:8b")
            self.assertEqual(payload["stream"], False)
            self.assertEqual(payload["think"], False)
            self.assertEqual(payload["options"]["temperature"], 0)
            self.assertEqual(payload["options"]["num_ctx"], 4096)
            self.assertEqual(payload["format"]["type"], "object")
            self.assertIn("Создавать API", payload["messages"][1]["content"])
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Backend",
                "skills": [
                    {"name": "Проектирование HTTP API", "weight": 5},
                    {"name": "SQL", "weight": 4},
                    {"name": "Docker", "weight": 2},
                ],
            })}})

        text = "Создавать API для обработки заказов, работать с SQL. Docker будет плюсом. Зарплата 200–300 тыс. ₽ на руки."
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual(draft["source"], "llm")
        self.assertEqual(draft["specialization"], "Backend")
        self.assertEqual([item["name"] for item in draft["required_skills"]], ["HTTP API", "SQL", "Docker"])
        self.assertEqual([item["weight"] for item in draft["required_skills"]], [5, 4, 2])
        self.assertEqual((draft["salary_min"], draft["salary_max"], draft["salary_tax_type"]), (200000, 300000, "net"))
        self.assertIsNone(draft["required_grade"])

    async def test_invalid_model_weight_is_rejected(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Backend", "skills": [{"name": "Python", "weight": 9}]
            })}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            with self.assertRaises(ValueError):
                await suggest_need("Ищем Backend-разработчика для создания API и интеграции сервисов.", client)

    async def test_optional_skills_are_low_and_unmentioned_tools_are_removed(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Backend", "skills": [
                    {"name": "Python", "weight": 5},
                    {"name": "FastAPI", "weight": 5},
                    {"name": "PostgreSQL", "weight": 5},
                    {"name": "Redis", "weight": 4},
                    {"name": "Django ORM", "weight": 3},
                    {"name": "CI/CD", "weight": 2},
                    {"name": "Docker", "weight": 3},
                ],
            })}})

        text = "Нужен Backend-разработчик для API на Python и FastAPI с PostgreSQL. Redis будет плюсом. Docker не нужен."
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual(draft["required_skills"], [
            {"name": "Python", "weight": 5},
            {"name": "FastAPI", "weight": 5},
            {"name": "PostgreSQL", "weight": 5},
            {"name": "Redis", "weight": 2},
        ])

    async def test_tasks_without_stack_keep_functional_skills(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Backend", "skills": [
                    {"name": "API Design", "weight": 5},
                    {"name": "Database Design", "weight": 5},
                    {"name": "Authentication & Authorization", "weight": 5},
                    {"name": "Django ORM", "weight": 3},
                    {"name": "Log Management", "weight": 3},
                ],
            })}})

        text = "Нужен Backend-разработчик: проектировать API, хранить данные и настроить авторизацию. Технологии ещё не выбрали."
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual([item["name"] for item in draft["required_skills"]], ["HTTP API", "Проектирование БД", "Авторизация"])

    async def test_task_phrase_uses_catalog_name(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Mobile", "skills": [
                    {"name": "Kotlin", "weight": 5},
                    {"name": "Работа с API", "weight": 5},
                    {"name": "Docker", "weight": 3},
                ],
            })}})

        text = "Нужен Android-разработчик: Kotlin, работа с API и офлайн-хранение данных."
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual([item["name"] for item in draft["required_skills"]], ["Kotlin", "HTTP API"])

    async def test_behavior_based_recommendation_keeps_functional_skills(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Data Science / ML", "skills": [
                    {"name": "Машинное обучение", "weight": 5},
                    {"name": "Подготовка данных", "weight": 4},
                    {"name": "Оценка моделей", "weight": 4},
                    {"name": "Развёртывание моделей", "weight": 5},
                    {"name": "Анализ данных", "weight": 4},
                    {"name": "Продуктовые метрики", "weight": 3},
                    {"name": "Рекомендательные системы", "weight": 5},
                ],
            })}})

        text = ("Нужно внедрить ML-модель на сайт консалтинговой компании. Она будет "
                "анализировать поведение пользователей на сайте и затем предлагать им подходящие услуги.")
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual(len(draft["required_skills"]), 7)
        self.assertEqual(draft["required_skills"][-1], {"name": "Рекомендательные системы", "weight": 5})

    async def test_short_russian_ml_scoring_request_keeps_task_skills(self):
        def reply(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": json.dumps({
                "specialization": "Data Science / ML", "skills": [
                    {"name": "Машинное обучение", "weight": 5},
                    {"name": "Подготовка данных", "weight": 5},
                    {"name": "Оценка моделей", "weight": 5},
                    {"name": "Развёртывание моделей", "weight": 5},
                    {"name": "Анализ данных", "weight": 4},
                    {"name": "HTTP API", "weight": 4},
                    {"name": "Продуктовые метрики", "weight": 3},
                    {"name": "Мониторинг", "weight": 3},
                ],
            })}})

        text = "надо сделать мл сервис и внедрить на сайт по кредитному скорингу"
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual([skill["name"] for skill in draft["required_skills"]], [
            "Машинное обучение", "Подготовка данных", "Оценка моделей",
            "Развёртывание моделей", "Анализ данных", "HTTP API", "Мониторинг",
        ])


if __name__ == "__main__":
    unittest.main()
