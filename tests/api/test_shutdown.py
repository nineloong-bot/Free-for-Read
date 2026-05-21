from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def test_shutdown_returns_acknowledgement() -> None:
    client = TestClient(create_app())

    response = client.post("/shutdown")

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
