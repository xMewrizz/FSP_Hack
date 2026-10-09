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
            self.assertEqual(payload["stream"], False)
            self.assertEqual(payload["options"]["temperature"], 0)
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

        text = "Создавать API для обработки заказов и работать с хранилищем данных. Зарплата 200–300 тыс. ₽ на руки."
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            draft = await suggest_need(text, client)
        self.assertEqual(draft["source"], "llm")
        self.assertEqual(draft["specialization"], "Backend")
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


if __name__ == "__main__":
    unittest.main()
