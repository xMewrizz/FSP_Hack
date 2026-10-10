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


class OpenRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_need_draft_uses_openrouter_and_keeps_skill_checks(self):
        def reply(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "qwen/qwen3-14b")
            self.assertEqual(payload["response_format"]["type"], "json_schema")
            output_schema = payload["response_format"]["json_schema"]["schema"]
            self.assertEqual(set(output_schema["required"]), {"specialization", "skills"})
            self.assertFalse(output_schema["additionalProperties"])
            self.assertFalse(output_schema["$defs"]["SuggestedSkill"]["additionalProperties"])
            self.assertTrue(payload["provider"]["require_parameters"])
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "specialization": "Backend",
                "skills": [
                    {"name": "Python", "weight": 5},
                    {"name": "Docker", "weight": 5},
                    {"name": "Redis", "weight": 5},
                ],
            })}}]})

        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                draft = await suggest_need("Нужен Backend на Python. Docker будет плюсом, Redis не нужен.", client)
        self.assertEqual(draft["required_skills"], [
            {"name": "Python", "weight": 5}, {"name": "Docker", "weight": 2},
        ])

    async def test_missing_key_does_not_send_request(self):
        def unexpected(_: httpx.Request) -> httpx.Response:
            self.fail("Запрос без ключа не должен уходить")

        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": ""}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
                with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY"):
                    await suggest_need("Нужен Backend на Python и SQL для разработки API.", client)
                result = await evaluate_open_answer(
                    "OPEN-BE-01", "free_text", "Вопрос", "Эталон", ["Критерий"], "Ответ кандидата", client
                )
        self.assertEqual(result.evaluator, "fallback_heuristic")
        self.assertTrue(result.needs_manual_review)

    async def test_open_answer_uses_openrouter_and_returns_review_flag(self):
        criterion = "Названа проверка входных данных"

        def reply(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(payload["response_format"]["json_schema"]["name"], "open_answer_evaluation")
            self.assertIn("Ответ кандидата", payload["messages"][1]["content"])
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "score": 1.0,
                "passed": True,
                "criteria_breakdown": [{"criterion": criterion, "met": True, "explanation": "Есть"}],
                "general_feedback": "Проверка указана.",
            })}}]})

        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                result = await evaluate_open_answer(
                    "OPEN-BE-01", "free_text", "Вопрос", "Эталон", [criterion], "Ответ кандидата", client
                )
        self.assertEqual(result.evaluator, "llm_openrouter_qwen3_14b")
        self.assertEqual(result.criterion_scores[criterion], 1.0)
        self.assertFalse(result.needs_manual_review)

    async def test_reasoning_switch_and_usage_metrics(self):
        criterion = "Названа проверка входных данных"
        requests = []

        def reply(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "gen-test", "model": "qwen/qwen3-14b",
                "usage": {"prompt_tokens": 100, "completion_tokens": 30,
                          "completion_tokens_details": {"reasoning_tokens": 10}},
                "choices": [{"message": {"content": json.dumps({
                    "score": 1.0, "passed": True,
                    "criteria_breakdown": [{"criterion": criterion, "met": True, "explanation": "Есть"}],
                    "general_feedback": "Проверка указана.",
                })}}],
            })

        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                for enabled in (True, False):
                    metrics = {}
                    result = await evaluate_open_answer(
                        "OPEN-BE-01", "free_text", "Вопрос", "Эталон", [criterion],
                        "Ответ кандидата", client, reasoning_enabled=enabled, metrics=metrics,
                    )
                    self.assertEqual(result.score, 1.0)
                    self.assertEqual(metrics["generation_id"], "gen-test")
                    self.assertEqual(metrics["prompt_tokens"], 100)
                    self.assertEqual(metrics["reasoning_tokens"], 10)
                    self.assertGreaterEqual(metrics["request_ms"], 0)
        self.assertEqual([payload["reasoning"] for payload in requests],
                         [{"enabled": True}, {"enabled": False}])

    async def test_openrouter_http_failure_requires_review(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test-key"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
                result = await evaluate_open_answer(
                    "OPEN-BE-01", "free_text", "Вопрос", "Эталон", ["Критерий"], "Ответ кандидата", client
                )
        self.assertEqual(result.evaluator, "fallback_heuristic")
        self.assertTrue(result.needs_manual_review)


if __name__ == "__main__":
    unittest.main()
