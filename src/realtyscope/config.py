from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by RealtyScope services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    project_name: str = Field(default="RealtyScope", alias="PROJECT_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_user: str = Field(default="realtyscope", alias="POSTGRES_USER")
    postgres_password: str = Field(default="realtyscope", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="realtyscope", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="MLFLOW_TRACKING_URI",
    )
    active_model_name: str = Field(default="realtyscope-price-model", alias="ACTIVE_MODEL_NAME")

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
