import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from need_llm import suggest_need

app = FastAPI(title="FSP ML-service", version="0.1.0")


class NeedText(BaseModel):
    text: str = Field(min_length=20, max_length=5000)


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


@app.post("/parse-resume")
def parse_resume_stub():
    return {"todo": "LLM-парсинг PDF -> поля профиля"}


@app.post("/score-match")
def score_match_stub():
    return {"todo": "эмбеддинги + взвешенный скоринг по осям"}


@app.post("/task-variant")
def task_variant_stub():
    return {"todo": "вариант задания по сиду + перефразировка Qwen"}
