from fastapi import FastAPI

app = FastAPI(title="FSP ML-service", version="0.1.0")


@app.get("/health")
def health():
    # TODO: проверка доступности Ollama (Qwen 14B) + эмбеддингов
    return {"status": "ok", "model": "qwen2.5:14b (external ollama)"}


@app.post("/parse-resume")
def parse_resume_stub():
    return {"todo": "LLM-парсинг PDF -> поля профиля"}


@app.post("/score-match")
def score_match_stub():
    return {"todo": "эмбеддинги + взвешенный скоринг по осям"}


@app.post("/task-variant")
def task_variant_stub():
    return {"todo": "вариант задания по сиду + перефразировка Qwen"}
