from realtyscope.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings()

    assert settings.project_name == "RealtyScope"
    assert settings.app_env == "local"
    assert settings.postgres_host == "localhost"
    assert settings.redis_host == "localhost"
    assert settings.mlflow_tracking_uri == "http://localhost:5000"


def test_database_url_uses_localhost_by_default() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    )
