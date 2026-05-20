from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


class StubLibraryService:
    def initialize(self) -> None:
        return None


def test_create_app_exposes_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_accepts_library_service() -> None:
    app = create_app(library_service=StubLibraryService())

    assert app.title == "Free for Read"
