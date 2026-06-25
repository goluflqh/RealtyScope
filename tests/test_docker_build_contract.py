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
