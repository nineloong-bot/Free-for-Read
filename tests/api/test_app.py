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


def test_create_app_registers_ai_routes_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "stub")
    monkeypatch.setenv("EMBED_PROVIDER", "stub")

    client = TestClient(create_app(storage_root=tmp_path / "storage"))

    response = client.get("/v1/books/search?q=test")

    assert response.status_code == 200
    assert response.json() == {"results": []}
