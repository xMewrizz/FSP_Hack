"""Compare Qwen grading with reasoning enabled and disabled on fixed answers.

Run from the repository root: python ml-service/benchmark_reasoning_latency.py
Only timing, token counts and scores are printed; prompts and API keys are not logged.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.open_question_bank import get_open_question_by_code
from benchmark_dataset import BENCHMARK_CASES
from open_evaluator import evaluate_open_answer


CASE_IDS = (
    "be_arch_01_ideal_senior",
    "be_arch_05_partial_race_condition",
    "be_arch_06_weak_superficial",
)


def load_local_key() -> None:
    if os.getenv("OPENROUTER_API_KEY"):
        return
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        raise RuntimeError("Добавьте OPENROUTER_API_KEY в окружение или корневой .env")
    for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            os.environ["OPENROUTER_API_KEY"] = line.split("=", 1)[1].strip().strip("\"'")
            break
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY не задан")


async def generation_details(client: httpx.AsyncClient, generation_id: str | None) -> dict:
    if not generation_id:
        return {"metadata_status": "no_generation_id"}
    # OpenRouter may return 404 briefly until generation metadata is indexed.
    for attempt in range(4):
        if attempt:
            await asyncio.sleep(attempt * 2)
        try:
            response = await client.get(
                "https://openrouter.ai/api/v1/generation",
                params={"id": generation_id},
                headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            )
            response.raise_for_status()
            data = response.json().get("data") or {}
            return {key: data.get(key) for key in (
                "provider_name", "latency", "generation_time", "native_tokens_prompt",
                "native_tokens_completion", "native_tokens_reasoning", "total_cost",
            )}
        except (httpx.HTTPError, ValueError) as exc:
            error = type(exc).__name__
            if isinstance(exc, httpx.HTTPStatusError):
                error = f"HTTP {exc.response.status_code}"
    return {"metadata_status": error}


async def main() -> None:
    load_local_key()
    os.environ["LLM_PROVIDER"] = "openrouter"
    case_ids = tuple(sys.argv[1:]) or CASE_IDS
    cases = {case["id"]: case for case in BENCHMARK_CASES if case["id"] in case_ids}
    if len(cases) != len(case_ids):
        raise RuntimeError("Не все контрольные ответы найдены")
    async with httpx.AsyncClient(timeout=120.0) as client:
        for index, case_id in enumerate(case_ids):
            case = cases[case_id]
            question = get_open_question_by_code(case["question_code"])
            if question is None:
                raise RuntimeError(f"Нет вопроса {case['question_code']}")
            # Alternate order so a warm provider does not systematically favor one mode.
            for enabled in ((True, False) if index % 2 == 0 else (False, True)):
                metrics: dict = {}
                started = time.perf_counter()
                result = await evaluate_open_answer(
                    question_code=question["code"],
                    question_type=question["question_type"],
                    question_text=question["question_text"],
                    reference_solution=question["reference_solution"],
                    rubric_criteria=question["rubric_criteria"],
                    candidate_answer=case["answer_text"],
                    client=client,
                    reasoning_enabled=enabled,
                    metrics=metrics,
                )
                total_ms = round((time.perf_counter() - started) * 1000, 1)
                details = await generation_details(client, metrics.get("generation_id"))
                print({
                    "case": case_id,
                    "reasoning": enabled,
                    "expected_score": case["ground_truth"]["score"],
                    "score": result.score,
                    "evaluator": result.evaluator,
                    "total_ms": total_ms,
                    **{key: value for key, value in metrics.items() if key != "generation_id"},
                    **details,
                }, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
