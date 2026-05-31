from fastapi.testclient import TestClient

from services.api.app.main import app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "realtyscope-api",
        "status": "ok",
        "project": "RealtyScope",
        "environment": "local",
    }
