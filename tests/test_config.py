from realtyscope.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings()

    assert settings.project_name == "RealtyScope"
    assert settings.app_env == "local"
    assert settings.postgres_host == "localhost"
    assert settings.redis_host == "localhost"
    assert settings.mlflow_tracking_uri == "http://localhost:5000"
    assert (
        settings.active_model_artifact_path
        == "data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib"
    )
    assert settings.model_artifact_dir == "data/processed/models"
    assert settings.model_selection_mode == "best_metric"


def test_database_url_uses_localhost_by_default() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    )


def test_database_url_can_be_overridden_by_environment_alias() -> None:
    settings = Settings(DATABASE_URL="sqlite+pysqlite:///:memory:")

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_database_url_override_does_not_change_default() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    )
