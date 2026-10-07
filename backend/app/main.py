from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all не добавляет поля в уже существующую таблицу. Для баз,
        # созданных до B-05, добавляем настройки публикации без удаления данных.
        columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("candidate_profiles")}
        )
        if "agreed_publication" not in columns:
            await conn.execute(text(
                "ALTER TABLE candidate_profiles ADD COLUMN agreed_publication BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        if "agreed_publication_at" not in columns:
            await conn.execute(text(
                "ALTER TABLE candidate_profiles ADD COLUMN agreed_publication_at TIMESTAMP NULL"
            ))
        if "visibility_public" not in columns:
            await conn.execute(text(
                "ALTER TABLE candidate_profiles ADD COLUMN visibility_public BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        await conn.execute(text(
            "UPDATE candidate_profiles SET visibility_public = FALSE WHERE agreed_publication = FALSE AND visibility_public = TRUE"
        ))
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FSP Career Platform API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/v1/health", tags=["System"])
def health():
    return {"status": "ok"}


@app.get("/docs-health", tags=["System"])
def docs_health():
    return {"swagger": "/docs", "redoc": "/redoc"}
