from fastapi import FastAPI

app = FastAPI(title="FSP ML-service", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse-resume")
def parse_resume_stub():
    return {"todo": "LLM-парсинг PDF -> поля профиля"}


@app.post("/score-match")
def score_match_stub():
    return {"todo": "эмбеддинги + взвешенный скоринг по осям"}


@app.post("/task-variant")
def task_variant_stub():
    return {"todo": "вариант задания по сиду + перефразировка Qwen"}
