from pathlib import Path

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType, ParsedChapter, ParsedEbook
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def sample_parsed_book(title: str = "Service Book") -> ParsedEbook:
    return ParsedEbook(
        title=title,
        author="Ada",
        language="en",
        source_type=EbookSourceType.EPUB,
        chapters=[
            ParsedChapter(
                index=0,
                title="Opening",
                markdown="# Opening\n\nHello.",
                word_count=2,
                source_ref="chapter.xhtml",
            )
        ],
    )


def test_library_service_imports_and_lists_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
        parser=lambda content, filename: sample_parsed_book(),
    )
    service.initialize()

    detail = service.import_book(filename="service.epub", content=b"epub bytes")

    assert detail.book.title == "Service Book"
    assert service.list_books(limit=10, offset=0)[0].id == detail.book.id
    assert Path(tmp_path / "storage" / detail.book.storage_path).exists()


def test_library_service_validates_progress_chapter_belongs_to_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    service.initialize()

    with pytest.raises(ParseError) as exc_info:
        service.update_progress(
            book_id="missing",
            chapter_id="chapter_missing",
            position={"paragraph": 1},
        )

    assert exc_info.value.code == "book_not_found"


def test_library_service_rejects_cross_book_progress(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
        parser=lambda content, filename: sample_parsed_book(filename),
    )
    service.initialize()
    first = service.import_book(filename="first.epub", content=b"first")
    second = service.import_book(filename="second.epub", content=b"second")

    with pytest.raises(ParseError) as exc_info:
        service.update_progress(
            book_id=first.book.id,
            chapter_id=second.chapters[0].id,
            position={"paragraph": 1},
        )

    assert exc_info.value.code == "chapter_not_found"


def test_library_service_list_chapters_requires_existing_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    service.initialize()

    with pytest.raises(ParseError) as exc_info:
        service.list_chapters("missing")

    assert exc_info.value.code == "book_not_found"


def test_library_service_validates_bookmark_chapter_belongs_to_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
        parser=lambda content, filename: sample_parsed_book(filename),
    )
    service.initialize()
    first = service.import_book(filename="first.epub", content=b"first")
    second = service.import_book(filename="second.epub", content=b"second")

    with pytest.raises(ParseError) as exc_info:
        service.create_bookmark(
            book_id=first.book.id,
            chapter_id=second.chapters[0].id,
            position={"paragraph": 1},
            label=None,
        )

    assert exc_info.value.code == "chapter_not_found"


def test_library_service_validates_bookmark_book_exists_before_chapter(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    service.initialize()

    with pytest.raises(ParseError) as exc_info:
        service.create_bookmark(
            book_id="missing",
            chapter_id="chapter_missing",
            position={"paragraph": 1},
            label=None,
        )

    assert exc_info.value.code == "book_not_found"


def test_library_service_get_progress_requires_existing_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    service.initialize()

    with pytest.raises(ParseError) as exc_info:
        service.get_progress("missing")

    assert exc_info.value.code == "book_not_found"
