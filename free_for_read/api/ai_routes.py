from typing import Protocol

from fastapi import APIRouter

from free_for_read.ai.rag import RagResponse
from free_for_read.api.ai_schemas import (
    ChatRequest,
    ChatResponse,
    IndexStatusResponse,
    ReindexResponse,
    SearchResponse,
)


class AiServiceProtocol(Protocol):
    async def query_book(
        self,
        book_id: str,
        question: str,
        *,
        top_k: int = 5,
        chapter_id: str | None = None,
        history: list[dict] | None = None,
    ) -> RagResponse: ...

    def search_books(
        self, q: str, *, limit: int = 10, book_id: str | None = None,
    ) -> list[dict]: ...

    def index_book(self, book_id: str) -> dict: ...

    def index_status(self, book_id: str) -> dict: ...


def create_ai_router(ai_service: AiServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1/books")

    @router.post("/{book_id}/chat", response_model=ChatResponse)
    async def chat(book_id: str, request: ChatRequest) -> RagResponse:
        return await ai_service.query_book(
            book_id,
            request.question,
            chapter_id=request.chapter_id,
            history=request.history,
        )

    @router.get("/search", response_model=SearchResponse)
    def search(q: str, limit: int = 10, book_id: str | None = None) -> dict:
        results = ai_service.search_books(q, limit=limit, book_id=book_id)
        return {"results": results}

    @router.post("/{book_id}/reindex", response_model=ReindexResponse)
    def reindex(book_id: str) -> dict:
        return ai_service.index_book(book_id)

    @router.get("/{book_id}/index", response_model=IndexStatusResponse)
    def index_status(book_id: str) -> dict:
        return ai_service.index_status(book_id)

    return router
