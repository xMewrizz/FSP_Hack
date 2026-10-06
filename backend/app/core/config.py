from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FSP Career API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg://fsp:fsp_secret@localhost:5432/fsp_career"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    FSP_MOCK_MODE: bool = True
    FSP_API_URL: str | None = None
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "fsp"
    KEYCLOAK_CLIENT_ID: str = "fsp-client"
    KEYCLOAK_CLIENT_SECRET: str = "fsp-secret"

    ML_SERVICE_URL: str = "http://localhost:8001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
