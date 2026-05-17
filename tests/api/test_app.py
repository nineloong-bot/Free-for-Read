from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def test_create_app_exposes_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
