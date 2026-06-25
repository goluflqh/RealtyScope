from pathlib import Path


def test_github_actions_enforces_minimum_pytest_coverage() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "pytest" in workflow
    assert "--cov=realtyscope" in workflow
    assert "--cov=services" in workflow
    assert "--cov-fail-under=50" in workflow
