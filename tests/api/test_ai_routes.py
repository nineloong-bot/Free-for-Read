from fastapi.testclient import TestClient

from free_for_read.ai.rag import RagResponse
from free_for_read.api.app import create_app


class StubAiService:
    async def query_book(self, book_id: str, question: str, *, top_k: int = 5) -> RagResponse:
        return RagResponse(
            answer="Test answer",
            sources=[{
                "chapter_id": "c1", "chapter_title": "Ch 1",
                "heading_path": "Ch 1", "text": "red bank base",
                "relevance": 0.95,
            }],
            model="stub",
            processing_ms=50,
        )

    def search_books(self, q: str, *, limit: int = 10, book_id: str | None = None) -> list[dict]:
        return [
            {"book_id": "b1", "book_title": "Test", "chapter_id": "c1",
             "chapter_title": "Ch 1", "text": "matched", "score": 0.9}
        ]


def test_chat_endpoint_returns_answer_with_sources() -> None:
    client = TestClient(create_app(ai_service=StubAiService()))

    resp = client.post("/v1/books/b1/chat", json={"question": "test?"})

    assert resp.status_code == 200
    assert resp.json()["answer"] == "Test answer"
    assert len(resp.json()["sources"]) == 1


def test_search_endpoint_returns_results() -> None:
    client = TestClient(create_app(ai_service=StubAiService()))

    resp = client.get("/v1/books/search?q=test")

    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1
    assert resp.json()["results"][0]["score"] == 0.9
