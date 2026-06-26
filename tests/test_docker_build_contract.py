from __future__ import annotations

from pathlib import Path

DOCKERFILES = [
    Path("services/api/Dockerfile"),
    Path("services/streamlit/Dockerfile"),
    Path("services/trainer/Dockerfile"),
]


def test_service_dockerfiles_cache_dependency_sync_before_copying_source() -> None:
    for dockerfile_path in DOCKERFILES:
        content = dockerfile_path.read_text(encoding="utf-8")
        source_copy_index = content.index("COPY --from=app_src . ./src")
        dependency_sync_index = content.index("uv sync")
        project_install_index = content.index("uv pip install")

        assert dependency_sync_index < source_copy_index, dockerfile_path
        assert "--no-install-project" in content, dockerfile_path
        assert source_copy_index < project_install_index, dockerfile_path
        assert "--no-deps ." in content, dockerfile_path


def test_streamlit_image_installs_database_dependencies_used_by_app_imports() -> None:
    content = Path("services/streamlit/Dockerfile").read_text(encoding="utf-8")

    assert "--extra streamlit" in content
    assert "--extra data" in content


def test_production_compose_mounts_runtime_assets_used_by_streamlit() -> None:
    content = Path("docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "API_BASE_URL: ${STREAMLIT_API_BASE_URL:-http://api:8000}" in content
    assert "./data/external:/app/data/external:ro" in content
    assert "model_artifacts:/app/data/processed/models:ro" in content


def test_production_env_points_streamlit_to_public_api_domain() -> None:
    content = Path(".env.production.example").read_text(encoding="utf-8")

    assert "STREAMLIT_API_BASE_URL=https://api.realtyscope.bond" in content


def test_production_caddy_serves_site_and_api_robots_txt() -> None:
    content = Path("deploy/caddy/Caddyfile").read_text(encoding="utf-8")

    assert "respond /robots.txt `User-agent: *\nAllow: /\n` 200" in content
    assert "respond /robots.txt `User-agent: *\nDisallow: /\n` 200" in content
