from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def test_shutdown_rejects_requests_without_token() -> None:
    client = TestClient(create_app(shutdown_token="secret"))

    response = client.post("/shutdown")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "shutdown_forbidden"


def test_shutdown_returns_acknowledgement_with_token() -> None:
    client = TestClient(create_app(shutdown_token="secret"))

    response = client.post("/shutdown", headers={"x-free-for-read-shutdown-token": "secret"})

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
