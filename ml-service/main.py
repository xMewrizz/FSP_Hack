import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from need_llm import suggest_need
from open_evaluator import OpenEvaluationResult, evaluate_open_answer

app = FastAPI(title="FSP ML-service", version="0.1.0")


class NeedText(BaseModel):
    text: str = Field(min_length=20, max_length=5000)


class OpenAnswerEvaluationRequest(BaseModel):
    question_code: str
    question_type: str = "free_text"
    question_text: str
    reference_solution: str
    rubric_criteria: list[str]
    critical_criteria: list[int] = Field(default_factory=list)
    candidate_answer: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse-need")
async def parse_need_text(data: NeedText):
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            return await suggest_need(data.text, client)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="Не удалось получить предложения от модели") from None


@app.post("/evaluate-open-answer", response_model=OpenEvaluationResult)
async def evaluate_open_answer_endpoint(payload: OpenAnswerEvaluationRequest):
    async with httpx.AsyncClient(timeout=120.0) as client:
        return await evaluate_open_answer(
            question_code=payload.question_code,
            question_type=payload.question_type,
            question_text=payload.question_text,
            reference_solution=payload.reference_solution,
            rubric_criteria=payload.rubric_criteria,
            critical_criteria=payload.critical_criteria,
            candidate_answer=payload.candidate_answer,
            client=client,
        )


@app.post("/parse-resume")
def parse_resume_stub():
    return {"todo": "LLM-парсинг PDF -> поля профиля"}


@app.post("/score-match")
def score_match_stub():
    return {"todo": "эмбеддинги + взвешенный скоринг по осям"}


@app.post("/task-variant")
def task_variant_stub():
    return {"todo": "вариант задания по сиду + перефразировка Qwen"}

