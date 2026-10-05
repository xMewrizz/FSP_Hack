from fastapi import FastAPI

app = FastAPI(title="FSP.Career API", version="0.1.0")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/docs-health")
def docs_health():
    return {"swagger": "/docs"}
