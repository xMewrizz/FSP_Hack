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
        if "verified_specialization" not in columns:
            await conn.execute(text(
                "ALTER TABLE candidate_profiles ADD COLUMN verified_specialization VARCHAR(100)"
            ))
            await conn.execute(text(
                "UPDATE candidate_profiles SET verified_specialization = specialization WHERE verified_grade IS NOT NULL"
            ))
        if "programming_language" not in columns:
            await conn.execute(text("ALTER TABLE candidate_profiles ADD COLUMN programming_language VARCHAR(50)"))
            await conn.execute(text("UPDATE candidate_profiles SET programming_language = 'Python' WHERE specialization = 'Backend'"))
        test_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("test_sessions")}
        )
        if "assessment_id" not in test_columns:
            await conn.execute(text("ALTER TABLE test_sessions ADD COLUMN assessment_id UUID"))
        if "skill_code" not in test_columns:
            await conn.execute(text("ALTER TABLE test_sessions ADD COLUMN skill_code VARCHAR(50)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_test_sessions_assessment_id ON test_sessions (assessment_id)"
        ))
        assessment_fk_exists = await conn.run_sync(
            lambda sync_conn: any(
                key["constrained_columns"] == ["assessment_id"]
                for key in inspect(sync_conn).get_foreign_keys("test_sessions")
            )
        )
        if not assessment_fk_exists:
            await conn.execute(text(
                "ALTER TABLE test_sessions ADD CONSTRAINT fk_test_sessions_assessment_id "
                "FOREIGN KEY (assessment_id) REFERENCES grade_assessments(id) ON DELETE CASCADE"
            ))
        assessment_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("grade_assessments")}
        )
        if "programming_language" not in assessment_columns:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD COLUMN programming_language VARCHAR(50)"
            ))
            await conn.execute(text(
                "UPDATE grade_assessments SET programming_language = 'Python' WHERE specialization = 'Backend'"
            ))
        if "question_codes" not in assessment_columns:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD COLUMN question_codes JSON NOT NULL DEFAULT '{}'"
            ))
        if "question_snapshots" not in assessment_columns:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD COLUMN question_snapshots JSON NOT NULL DEFAULT '{}'"
            ))
        if "retake_question_snapshots" not in assessment_columns:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD COLUMN retake_question_snapshots JSON NOT NULL DEFAULT '{}'"
            ))
        if "retake_of_id" not in assessment_columns:
            await conn.execute(text("ALTER TABLE grade_assessments ADD COLUMN retake_of_id UUID"))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_grade_assessments_retake_of_id "
            "ON grade_assessments (retake_of_id)"
        ))
        retake_fk_exists = await conn.run_sync(
            lambda sync_conn: any(
                key["constrained_columns"] == ["retake_of_id"]
                for key in inspect(sync_conn).get_foreign_keys("grade_assessments")
            )
        )
        if not retake_fk_exists:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD CONSTRAINT fk_grade_assessments_retake_of_id "
                "FOREIGN KEY (retake_of_id) REFERENCES grade_assessments(id) ON DELETE SET NULL"
            ))
        if "scoring_policy" not in assessment_columns:
            await conn.execute(text(
                "ALTER TABLE grade_assessments ADD COLUMN scoring_policy JSON NOT NULL "
                "DEFAULT '{\"overall\": 0.75, \"skill\": 0.5}'"
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
