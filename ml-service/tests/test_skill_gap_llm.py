import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skill_gap_llm import MissedAnswer, recommend_topics


class SkillGapLlmTests(unittest.IsolatedAsyncioTestCase):
    async def test_perfect_score_does_not_call_model(self):
        def unexpected(_: httpx.Request) -> httpx.Response:
            self.fail("При отсутствии ошибок запрос к модели не отправляется")

        async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
            topics = await recommend_topics([], client, skill="Python", specialization="Data Science / ML", grade="junior")
        self.assertEqual(topics, [])

    async def test_only_supplied_wrong_answers_are_sent(self):
        def reply(request: httpx.Request) -> httpx.Response:
            self.assertNotIn("OPENROUTER_API_KEY", request.content.decode("utf-8"))
            payload = json.loads(request.content)
            content = payload["messages"][1]["content"]
            self.assertIn("list.copy", content)
            self.assertIn("KeyError", content)
            self.assertNotIn("Этот ответ верный", content)
            self.assertEqual(content.count("Вопрос:"), 2)
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "topics": ["Поверхностная копия", "Обработка ValueError"],
            }, ensure_ascii=False)}}]})

        missed = [
            MissedAnswer(question="Что делает list.copy для вложенных списков?", answer="Копирует всё рекурсивно"),
            MissedAnswer(question="Какое исключение вызывает int('abc')?", answer="KeyError"),
        ]
        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                topics = await recommend_topics(
                    missed, client, skill="Python", specialization="Data Science / ML", grade="junior",
                )
        self.assertEqual(topics, ["Поверхностная копия", "Обработка ValueError"])

    async def test_request_is_capped_at_ten_wrong_answers(self):
        def reply(request: httpx.Request) -> httpx.Response:
            content = json.loads(request.content)["messages"][1]["content"]
            self.assertEqual(content.count("Вопрос:"), 10)
            self.assertNotIn("Вопрос номер 11", content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "{\"topics\": [\"Тема\"]}"}}]})

        missed = [
            MissedAnswer(question=f"Вопрос номер {index}", answer="неверно")
            for index in range(1, 12)
        ]
        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                topics = await recommend_topics(
                    missed, client, skill="SQL", specialization="Backend", grade="junior",
                )
        self.assertEqual(topics, ["Тема"])
