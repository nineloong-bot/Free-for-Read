from fastapi.testclient import TestClient

from free_for_read.ai.embeddings import StubEmbeddingProvider
from free_for_read.ai.llm import StubLlmProvider
from free_for_read.ai.service import AiService
from free_for_read.api.app import create_app
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def test_import_index_chat_search(tmp_path) -> None:
    """End-to-end: import book, index, chat, search."""
    ai = AiService(
        repository=SQLiteLibraryRepository(tmp_path / "lib.sqlite3"),
        chroma_path=tmp_path / "chroma",
        llm=StubLlmProvider(),
        embeddings=StubEmbeddingProvider(),
    )
    library = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=ai.repository,
        parser=lambda content, filename: type('obj', (), {
            'title': 'Test Book',
            'author': 'Ada',
            'language': 'en',
            'source_type': type('obj', (), {'value': 'epub'}),
            'chapters': [type('obj', (), {
                'index': 0,
                'title': 'Ch1',
                'markdown': '# Ch1\n\nTest content for searching.',
                'word_count': 5,
                'source_ref': 'c1.xhtml',
                'metadata': {},
            })],
            'chapter_count': 1,
            'word_count': 5,
            'cover_path': None,
            'metadata': {},
        })(),
    )
    client = TestClient(create_app(
        library_service=library,
        ai_service=ai,
        storage_root=tmp_path / "storage",
    ))

    # Import book
    import_resp = client.post(
        "/v1/books/import",
        files={"file": ("test.epub", b"data", "application/epub+zip")},
    )
    assert import_resp.status_code == 200
    book_id = import_resp.json()["book"]["id"]

    # Index book
    reindex_resp = client.post(f"/v1/books/{book_id}/reindex")
    assert reindex_resp.status_code == 200
    assert reindex_resp.json()["status"] == "indexed"
    assert reindex_resp.json()["chunk_count"] > 0

    # Check index status
    status_resp = client.get(f"/v1/books/{book_id}/index")
    assert status_resp.status_code == 200
    assert status_resp.json()["indexed"] is True

    # Chat
    chat_resp = client.post(
        f"/v1/books/{book_id}/chat",
        json={"question": "what is this about?"},
    )
    assert chat_resp.status_code == 200
    assert "Stub response" in chat_resp.json()["answer"]
    assert len(chat_resp.json()["sources"]) > 0

    # Search
    search_resp = client.get("/v1/books/search?q=test")
    assert search_resp.status_code == 200
    assert len(search_resp.json()["results"]) > 0
