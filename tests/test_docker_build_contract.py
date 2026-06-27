from __future__ import annotations

import re
import tomllib
from pathlib import Path

DOCKERFILES = [
    Path("services/api/Dockerfile"),
    Path("services/streamlit/Dockerfile"),
    Path("services/trainer/Dockerfile"),
]
PYPROJECTS = [
    Path("pyproject.toml"),
    Path("docker/build/deps/pyproject.toml"),
]
LOCKFILES = [
    Path("uv.lock"),
    Path("docker/build/deps/uv.lock"),
]
TRAINED_ARTIFACT_SKLEARN_VERSION = "1.6.1"


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


def test_runtime_dependencies_pin_sklearn_to_trained_artifact_version() -> None:
    expected = f"scikit-learn=={TRAINED_ARTIFACT_SKLEARN_VERSION}"
    for pyproject_path in PYPROJECTS:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        assert expected in pyproject["project"]["dependencies"], pyproject_path


def test_uv_locks_resolve_sklearn_to_trained_artifact_version() -> None:
    for lockfile_path in LOCKFILES:
        content = lockfile_path.read_text(encoding="utf-8")
        match = re.search(
            r'name = "scikit-learn"\s+version = "([^"]+)"',
            content,
            flags=re.MULTILINE,
        )

        assert match, lockfile_path
        assert match.group(1) == TRAINED_ARTIFACT_SKLEARN_VERSION, lockfile_path
        assert 'specifier = "==1.6.1"' in content, lockfile_path


def test_streamlit_image_installs_database_dependencies_used_by_app_imports() -> None:
    content = Path("services/streamlit/Dockerfile").read_text(encoding="utf-8")

    assert "--extra streamlit" in content
    assert "--extra data" in content


def test_production_compose_mounts_runtime_assets_used_by_streamlit() -> None:
    content = Path("docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "API_BASE_URL: http://api:8000" in content
    assert (
        "BROWSER_API_BASE_URL: ${STREAMLIT_API_BASE_URL:?set STREAMLIT_API_BASE_URL in .env}"
        in content
    )
    assert (
        "STREAMLIT_INITIAL_LISTING_ROW_LIMIT: ${STREAMLIT_INITIAL_LISTING_ROW_LIMIT:-20000}"
        in content
    )
    assert (
        "STREAMLIT_INITIAL_MAP_POINT_LIMIT: ${STREAMLIT_INITIAL_MAP_POINT_LIMIT:-20000}" in content
    )
    assert "./data/external:/app/data/external:ro" in content
    assert "model_artifacts:/app/data/processed/models:ro" in content


def test_production_compose_defines_dockerized_ingestor_job() -> None:
    content = Path("docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "  ingestor:" in content
    assert 'profiles: ["jobs"]' in content
    assert "python -m realtyscope.ingestion.domclick_scheduled_batch" in content
    assert "./data/raw:/app/data/raw" in content
    assert "./data/processed:/app/data/processed" in content


def test_gitignore_excludes_local_databases_and_runtime_transfer_bundles() -> None:
    content = Path(".gitignore").read_text(encoding="utf-8")

    assert "data/*.db" in content
    assert "data/*.sqlite" in content
    assert "realtyscope-db-*.dump" in content
    assert "realtyscope-model-artifacts-*.tar.gz" in content


def test_dev_compose_mounts_district_boundary_assets_used_by_streamlit() -> None:
    content = Path("docker-compose.yml").read_text(encoding="utf-8")

    streamlit_section = content[content.index("  streamlit:") : content.index("  trainer:")]

    assert "API_BASE_URL: http://api:8000" in streamlit_section
    assert "BROWSER_API_BASE_URL: http://localhost:8000" in streamlit_section
    assert "STREAMLIT_INITIAL_LISTING_ROW_LIMIT: 20000" in streamlit_section
    assert "STREAMLIT_INITIAL_MAP_POINT_LIMIT: 20000" in streamlit_section
    assert "./data/external:/app/data/external:ro" in streamlit_section


def test_production_env_points_streamlit_to_public_api_domain() -> None:
    content = Path(".env.production.example").read_text(encoding="utf-8")

    assert "STREAMLIT_API_BASE_URL=https://api.realtyscope.bond" in content
    assert "STREAMLIT_INITIAL_LISTING_ROW_LIMIT=20000" in content
    assert "STREAMLIT_INITIAL_MAP_POINT_LIMIT=20000" in content


def test_production_caddy_serves_site_and_api_robots_txt() -> None:
    content = Path("deploy/caddy/Caddyfile").read_text(encoding="utf-8")

    assert "respond /robots.txt `User-agent: *\nAllow: /\n` 200" in content
    assert "respond /robots.txt `User-agent: *\nDisallow: /\n` 200" in content
