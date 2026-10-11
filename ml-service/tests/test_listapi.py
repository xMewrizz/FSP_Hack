"""Контракт OpenAI-совместимого API для подсказок и оценки заданий."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from need_llm import suggest_need
from open_evaluator import evaluate_open_answer


class ListApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_temporary_upstream_failure_once(self):
        requests = 0

        def reply(_: httpx.Request) -> httpx.Response:
            nonlocal requests
            requests += 1
            if requests == 1:
                return httpx.Response(503)
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "specialization": "Backend", "skills": [{"name": "Python", "weight": 5}],
            })}}]})

        with patch.dict(os.environ, {"LLM_PROVIDER": "listapi", "LIST_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                result = await suggest_need("Нужен Backend на Python", client)
        self.assertEqual(requests, 2)
        self.assertEqual(result["required_skills"], [{"name": "Python", "weight": 5}])

    async def test_need_uses_strict_schema_without_openrouter_fields(self):
        def reply(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://list-api.listapi.workers.dev/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "gpt-5.6-sol")
            self.assertEqual(body["response_format"]["type"], "json_schema")
            self.assertNotIn("provider", body)
            self.assertNotIn("temperature", body)
            self.assertNotIn("reasoning", body)
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "specialization": "Backend", "skills": [{"name": "Python", "weight": 5}],
            })}}]})

        with patch.dict(os.environ, {"LLM_PROVIDER": "listapi", "LIST_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                result = await suggest_need("Нужен Backend на Python", client)
        self.assertEqual(result["required_skills"], [{"name": "Python", "weight": 5}])

    async def test_open_answer_marks_provider(self):
        criterion = "Названа проверка входных данных"

        def reply(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            self.assertEqual(body["response_format"]["json_schema"]["name"], "open_answer_evaluation")
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "score": 1.0, "passed": True,
                "criteria_breakdown": [{"criterion": criterion, "met": True, "explanation": "Есть"}],
                "general_feedback": "Проверка указана.",
            })}}]})

        with patch.dict(os.environ, {"LLM_PROVIDER": "listapi", "LIST_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                result = await evaluate_open_answer(
                    "OPEN-BE-01", "free_text", "Вопрос", "Эталон", [criterion], "Ответ", client,
                )
        self.assertEqual(result.evaluator, "llm_listapi")
        self.assertEqual(result.criterion_scores[criterion], 1.0)
        self.assertFalse(result.needs_manual_review)

    async def test_missing_key_keeps_open_answer_ungraded(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "listapi", "LIST_API_KEY": ""}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda _: self.fail("Запрос без ключа не должен уходить"),
            )) as client:
                result = await evaluate_open_answer(
                    "OPEN-BE-01", "free_text", "Вопрос", "Эталон", ["Критерий"], "Ответ", client,
                )
        self.assertEqual(result.evaluator, "fallback_heuristic")
        self.assertTrue(result.needs_manual_review)


if __name__ == "__main__":
    unittest.main()
