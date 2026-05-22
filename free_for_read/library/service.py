from collections.abc import Callable
from pathlib import Path
from typing import Any

from free_for_read.core.errors import ParseError
from free_for_read.library.models import (
    Book,
    BookDetail,
    Bookmark,
    Chapter,
    ParsedEbook,
    ReadingProgress,
)
from free_for_read.library.repository import LibraryRepository
from free_for_read.library.storage import StorageBackend
from free_for_read.parsers.ebooks import parse_ebook

EbookParser = Callable[[bytes, str], ParsedEbook]


class LibraryService:
    def __init__(
        self,
        *,
        storage: StorageBackend,
        repository: LibraryRepository,
        parser: EbookParser | None = None,
    ) -> None:
        self.storage = storage
        self.repository = repository
        self.parser = parser or (lambda content, filename: parse_ebook(content, filename=filename))

    def initialize(self) -> None:
        self.repository.initialize()

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        parsed = self.parser(content, filename)
        storage_path = self.storage.save(filename, content)
        return self.repository.create_book(
            parsed=parsed,
            original_filename=filename,
            storage_path=storage_path,
        )

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        return self.repository.list_books(limit=limit, offset=offset)

    def get_book(self, book_id: str) -> BookDetail:
        return self.repository.get_book(book_id)

    def get_source_path(self, book_id: str) -> Path:
        detail = self.repository.get_book(book_id)
        path = self.storage.path_for(detail.book.storage_path)
        if not path.exists() or not path.is_file():
            raise ParseError(
                code="storage_failed",
                message="Stored source file was not found.",
                details={"book_id": book_id},
            )
        return path

    def list_chapters(self, book_id: str) -> list[Chapter]:
        self.repository.get_book(book_id)
        return self.repository.list_chapters(book_id)

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        return self.repository.get_chapter(book_id, chapter_id)

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        self.repository.get_book(book_id)
        return self.repository.get_progress(book_id)

    def update_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        self.repository.get_book(book_id)
        return self.repository.upsert_progress(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
        )

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        self.repository.get_book(book_id)
        return self.repository.create_bookmark(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            label=label,
        )

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        self.repository.get_book(book_id)
        return self.repository.list_bookmarks(book_id)

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        self.repository.get_book(book_id)
        self.repository.delete_bookmark(book_id, bookmark_id)

    def delete_book(self, book_id: str) -> None:
        self.repository.get_book(book_id)
        self.repository.delete_book(book_id)
