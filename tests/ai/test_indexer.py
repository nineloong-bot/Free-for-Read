import tempfile
from pathlib import Path

from free_for_read.ai.embeddings import StubEmbeddingProvider
from free_for_read.ai.indexer import BookIndexer


def test_indexer_create_and_query_collection() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(
            chroma_path=Path(tmpdir),
            embeddings=StubEmbeddingProvider(),
        )
        chunks = [
            {
                "id": "c1", "text": "红岸基地的秘密计划",
                "chapter_title": "Chapter 1", "heading_path": "Chapter 1",
            },
            {
                "id": "c2", "text": "叶文洁按下发射按钮",
                "chapter_title": "Chapter 2", "heading_path": "Chapter 2",
            },
        ]

        indexer.index_book("book_test", chunks)

        results = indexer.query("book_test", "红岸基地", top_k=1)
        assert len(results) == 1
        assert "id" in results[0]
        assert "text" in results[0]


def test_indexer_handles_empty_chunks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(
            chroma_path=Path(tmpdir),
            embeddings=StubEmbeddingProvider(),
        )
        indexer.index_book("book_empty", [])
        results = indexer.query("book_empty", "anything", top_k=1)
        assert len(results) == 0
