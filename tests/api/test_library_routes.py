from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.core.errors import ParseError
from free_for_read.library.models import (
    Book,
    BookDetail,
    Bookmark,
    Chapter,
    EbookSourceType,
    ReadingProgress,
)


class StubLibraryService:
    def __init__(self) -> None:
        self.book = Book(
            id="book_1",
            title="API Book",
            author="Ada",
            language="en",
            source_type=EbookSourceType.EPUB,
            original_filename="api.epub",
            storage_path="books/api.epub",
            cover_path=None,
            word_count=2,
            chapter_count=3,
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
        )
        self.chapters = [
            Chapter(
                id="chapter_1",
                book_id="book_1",
                index=0,
                title="Opening",
                markdown="# Opening\n\nHello.",
                word_count=2,
                source_ref="chapter-1.xhtml",
            ),
            Chapter(
                id="chapter_2",
                book_id="book_1",
                index=1,
                title="Middle",
                markdown="# Middle\n\nThere.",
                word_count=2,
                source_ref="chapter-2.xhtml",
            ),
            Chapter(
                id="chapter_3",
                book_id="book_1",
                index=2,
                title="Ending",
                markdown="# Ending\n\nBye.",
                word_count=2,
                source_ref="chapter-3.xhtml",
            ),
        ]
        self.progress: ReadingProgress | None = None
        self.bookmarks: list[Bookmark] = []
        self.source_path: Path | None = None

    def initialize(self) -> None:
        return None

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        assert filename == "api.epub"
        assert content == b"epub bytes"
        return BookDetail(book=self.book, chapters=self.chapters)

    def get_source_path(self, book_id: str) -> Path:
        self._raise_if_missing_book(book_id)
        if self.source_path is None:
            raise AssertionError("source_path must be set by the test")
        return self.source_path

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        assert limit == 50
        assert offset == 0
        return [self.book]

    def get_book(self, book_id: str) -> BookDetail:
        self._raise_if_missing_book(book_id)
        return BookDetail(book=self.book, chapters=self.chapters, progress=self.progress)

    def list_chapters(self, book_id: str) -> list[Chapter]:
        self._raise_if_missing_book(book_id)
        return self.chapters

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        self._raise_if_missing_book(book_id)
        for chapter in self.chapters:
            if chapter.id == chapter_id:
                return chapter
        raise ParseError(
            code="chapter_not_found",
            message="Chapter was not found",
            details={"book_id": book_id, "chapter_id": chapter_id},
        )

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        self._raise_if_missing_book(book_id)
        return self.progress

    def update_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        self.progress = ReadingProgress(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            updated_at="2026-05-20T00:00:00+00:00",
        )
        return self.progress

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        bookmark = Bookmark(
            id="bookmark_1",
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            label=label,
            created_at="2026-05-20T00:00:00+00:00",
        )
        self.bookmarks.append(bookmark)
        return bookmark

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        self._raise_if_missing_book(book_id)
        return self.bookmarks

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        self._raise_if_missing_book(book_id)
        assert bookmark_id == "bookmark_1"
        self.bookmarks = []

    def _raise_if_missing_book(self, book_id: str) -> None:
        if book_id != "book_1":
            raise ParseError(
                code="book_not_found",
                message="Book was not found",
                details={"book_id": book_id},
            )


def test_import_book_route_returns_book_detail() -> None:
    client = TestClient(create_app(library_service=StubLibraryService()))

    response = client.post(
        "/v1/books/import",
        files={"file": ("api.epub", b"epub bytes", "application/epub+zip")},
    )

    assert response.status_code == 200
    assert response.json()["book"]["title"] == "API Book"
    assert response.json()["chapters"][0]["title"] == "Opening"
    assert "markdown" not in response.json()["chapters"][0]


def test_import_book_rejects_oversized_upload() -> None:
    client = TestClient(
        create_app(
            library_service=StubLibraryService(),
            max_file_bytes=4,
        )
    )

    response = client.post(
        "/v1/books/import",
        files={"file": ("api.epub", b"12345", "application/epub+zip")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "content_too_large"


def test_get_book_source_returns_stored_source_file(tmp_path: Path) -> None:
    service = StubLibraryService()
    service.source_path = tmp_path / "api.epub"
    service.source_path.write_bytes(b"stored epub bytes")
    client = TestClient(create_app(library_service=service))

    response = client.get("/v1/books/book_1/source")

    assert response.status_code == 200
    assert response.content == b"stored epub bytes"


def test_book_chapter_progress_and_bookmark_routes() -> None:
    service = StubLibraryService()
    client = TestClient(create_app(library_service=service))

    books = client.get("/v1/books")
    assert books.status_code == 200
    assert books.json()["items"][0]["id"] == "book_1"

    book = client.get("/v1/books/book_1")
    assert book.status_code == 200
    assert book.json()["book"]["id"] == "book_1"

    chapters = client.get("/v1/books/book_1/chapters")
    assert chapters.status_code == 200
    assert chapters.json()["items"][0]["id"] == "chapter_1"

    chapter = client.get("/v1/books/book_1/chapters/chapter_1")
    assert chapter.status_code == 200
    assert chapter.json()["markdown"] == "# Opening\n\nHello."

    progress = client.put(
        "/v1/books/book_1/progress",
        json={"chapter_id": "chapter_1", "position": {"paragraph": 1}},
    )
    assert progress.status_code == 200
    assert progress.json()["position"] == {"paragraph": 1}

    saved_progress = client.get("/v1/books/book_1/progress")
    assert saved_progress.status_code == 200
    assert saved_progress.json()["chapter_id"] == "chapter_1"

    bookmark = client.post(
        "/v1/books/book_1/bookmarks",
        json={"chapter_id": "chapter_1", "position": {"paragraph": 1}, "label": "Start"},
    )
    assert bookmark.status_code == 200
    assert bookmark.json()["label"] == "Start"

    bookmarks = client.get("/v1/books/book_1/bookmarks")
    assert bookmarks.status_code == 200
    assert bookmarks.json()["items"][0]["id"] == "bookmark_1"

    assert client.delete("/v1/books/book_1/bookmarks/bookmark_1").status_code == 204


def test_list_chapters_for_missing_book_returns_404() -> None:
    client = TestClient(create_app(library_service=StubLibraryService()))

    response = client.get("/v1/books/missing/chapters")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "book_not_found"


def test_get_chapter_returns_previous_and_next_ids_for_multi_chapter_book() -> None:
    client = TestClient(create_app(library_service=StubLibraryService()))

    response = client.get("/v1/books/book_1/chapters/chapter_2")

    assert response.status_code == 200
    assert response.json()["previous_chapter_id"] == "chapter_1"
    assert response.json()["next_chapter_id"] == "chapter_3"


def test_list_books_rejects_invalid_limit() -> None:
    client = TestClient(
        create_app(library_service=StubLibraryService()),
        raise_server_exceptions=False,
    )

    response = client.get("/v1/books?limit=0")

    assert response.status_code == 422
