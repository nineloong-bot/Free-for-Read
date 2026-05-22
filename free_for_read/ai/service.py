import os
from pathlib import Path

from free_for_read.ai.chunking import chunk_chapter
from free_for_read.ai.embeddings import EmbeddingProvider, create_embedding_provider
from free_for_read.ai.indexer import BookIndexer
from free_for_read.ai.llm import LlmProvider, create_llm_provider
from free_for_read.ai.rag import RagPipeline, RagResponse
from free_for_read.library.repository import LibraryRepository


class AiService:
    def __init__(
        self,
        *,
        repository: LibraryRepository,
        chroma_path: Path | None = None,
        llm: LlmProvider | None = None,
        embeddings: EmbeddingProvider | None = None,
    ):
        self.repository = repository
        self._repository = repository
        storage_root = chroma_path or Path(os.environ.get("CHROMA_PATH", "storage/chroma"))
        self._embed_provider = embeddings or create_embedding_provider(
            os.environ.get("EMBED_PROVIDER", "local")
        )
        self._indexer = BookIndexer(chroma_path=storage_root, embeddings=self._embed_provider)
        self._llm = llm or create_llm_provider(os.environ.get("AI_PROVIDER", "stub"))
        self._rag = RagPipeline(llm=self._llm, indexer=self._indexer)

    async def query_book(
        self,
        book_id: str,
        question: str,
        *,
        top_k: int = 5,
        chapter_id: str | None = None,
        history: list[dict] | None = None,
    ) -> RagResponse:
        return await self._rag.query(
            book_id,
            question,
            top_k=top_k,
            chapter_id=chapter_id,
            history=history,
        )

    def search_books(self, q: str, *, limit: int = 10, book_id: str | None = None) -> list[dict]:
        books = self._repository.list_books(limit=10000, offset=0)
        book_ids = [b.id for b in books] if book_id is None else [book_id]
        titles = {b.id: b.title for b in books}

        results = self._rag.search(q, top_k=limit, book_ids=book_ids)
        for r in results:
            r.book_title = titles.get(r.book_id, "")
        return [r.model_dump() for r in results]

    def index_book(self, book_id: str) -> dict:
        chapters = self._repository.list_chapters(book_id)
        all_chunks = []
        for ch in chapters:
            chunks = chunk_chapter(
                ch.markdown, book_id=book_id, chapter_id=ch.id, chapter_title=ch.title,
            )
            all_chunks.extend([{
                "id": c.id, "text": c.text,
                "chapter_id": ch.id,
                "chapter_title": c.chapter_title, "heading_path": c.heading_path,
            } for c in chunks])
        self._indexer.index_book(book_id, all_chunks)
        return {"status": "indexed", "chunk_count": len(all_chunks)}

    def index_status(self, book_id: str) -> dict:
        indexed = self._indexer.collection_exists(book_id)
        return {"indexed": indexed, "chunk_count": None, "last_indexed": None}
