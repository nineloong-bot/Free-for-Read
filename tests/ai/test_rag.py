import tempfile
from pathlib import Path

import pytest

from free_for_read.ai.embeddings import StubEmbeddingProvider
from free_for_read.ai.indexer import BookIndexer
from free_for_read.ai.llm import StubLlmProvider
from free_for_read.ai.rag import RagPipeline, RagResponse, SearchResult


def test_rag_response_model() -> None:
    resp = RagResponse(
        answer="Test answer",
        sources=[{
            "chapter_id": "c1",
            "chapter_title": "Ch 1",
            "heading_path": "Ch 1",
            "text": "source text",
            "relevance": 0.95,
        }],
        model="stub",
        processing_ms=100,
    )
    assert resp.answer == "Test answer"
    assert len(resp.sources) == 1


@pytest.mark.asyncio
async def test_rag_pipeline_query() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(chroma_path=Path(tmpdir), embeddings=StubEmbeddingProvider())
        llm = StubLlmProvider()
        rag = RagPipeline(llm=llm, indexer=indexer)

        indexer.index_book("b1", [
            {
                "id": "c1", "text": "红岸基地的秘密计划",
                "chapter_title": "Ch 1", "heading_path": "Ch 1",
            },
        ])

        resp = await rag.query("b1", "红岸基地是什么？")

        assert isinstance(resp, RagResponse)
        assert len(resp.answer) > 0
        assert len(resp.sources) > 0


def test_search_result_model() -> None:
    result = SearchResult(
        book_id="b1", book_title="Test Book", chapter_id="c1",
        chapter_title="Ch 1", text="matched text", score=0.88,
    )
    assert result.score == 0.88
