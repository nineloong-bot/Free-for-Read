import sqlite3

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType, ParsedChapter, ParsedEbook
from free_for_read.library.repository import SQLiteLibraryRepository


def sample_parsed_book() -> ParsedEbook:
    return ParsedEbook(
        title="Stored Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.EPUB,
        chapters=[
            ParsedChapter(
                index=0,
                title="Opening",
                markdown="# Opening\n\nHello reader.",
                word_count=3,
                source_ref="chapter1.xhtml",
            ),
            ParsedChapter(
                index=1,
                title="Second",
                markdown="# Second\n\nAnother page.",
                word_count=3,
                source_ref="chapter2.xhtml",
            ),
        ],
    )


def test_repository_inserts_and_fetches_book_with_ordered_chapters(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()

    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    listed = repository.list_books(limit=10, offset=0)
    fetched = repository.get_book(detail.book.id)
    chapters = repository.list_chapters(detail.book.id)

    assert listed[0].id == detail.book.id
    assert fetched.book.title == "Stored Book"
    assert [chapter.title for chapter in chapters] == ["Opening", "Second"]
    assert fetched.chapters[1].markdown == "# Second\n\nAnother page."


def test_repository_initialize_creates_parent_directory(tmp_path) -> None:
    database_path = tmp_path / "missing" / "library.sqlite3"
    repository = SQLiteLibraryRepository(database_path)

    repository.initialize()

    assert database_path.exists()


def test_repository_upserts_progress(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    progress = repository.upsert_progress(
        book_id=detail.book.id,
        chapter_id=detail.chapters[0].id,
        position={"paragraph": 1},
    )
    updated = repository.upsert_progress(
        book_id=detail.book.id,
        chapter_id=detail.chapters[1].id,
        position={"paragraph": 2},
    )

    assert progress.book_id == detail.book.id
    assert updated.chapter_id == detail.chapters[1].id
    assert repository.get_progress(detail.book.id).position == {"paragraph": 2}


def test_upsert_progress_requires_chapter_from_matching_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    first = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="first.epub",
        storage_path="books/first.epub",
    )
    second = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="second.epub",
        storage_path="books/second.epub",
    )

    with pytest.raises(ParseError) as exc_info:
        repository.upsert_progress(
            book_id=first.book.id,
            chapter_id=second.chapters[0].id,
            position={"paragraph": 1},
        )
    assert exc_info.value.code == "chapter_not_found"


def test_repository_creates_lists_and_deletes_bookmarks(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    bookmark = repository.create_bookmark(
        book_id=detail.book.id,
        chapter_id=detail.chapters[0].id,
        position={"paragraph": 1},
        label="Start",
    )

    assert repository.list_bookmarks(detail.book.id)[0].label == "Start"
    repository.delete_bookmark(detail.book.id, bookmark.id)
    assert repository.list_bookmarks(detail.book.id) == []


def test_create_bookmark_requires_chapter_from_matching_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    first = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="first.epub",
        storage_path="books/first.epub",
    )
    second = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="second.epub",
        storage_path="books/second.epub",
    )

    with pytest.raises(ParseError) as exc_info:
        repository.create_bookmark(
            book_id=first.book.id,
            chapter_id=second.chapters[0].id,
            position={"paragraph": 1},
            label=None,
        )
    assert exc_info.value.code == "chapter_not_found"


def test_repository_raises_for_missing_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()

    try:
        repository.get_book("missing")
    except ParseError as exc:
        assert exc.code == "book_not_found"
    else:
        raise AssertionError("missing book should raise ParseError")


def test_get_chapter_requires_matching_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    first = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="first.epub",
        storage_path="books/first.epub",
    )
    second = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="second.epub",
        storage_path="books/second.epub",
    )

    chapter = repository.get_chapter(first.book.id, first.chapters[0].id)

    assert chapter.title == "Opening"
    with pytest.raises(ParseError) as exc_info:
        repository.get_chapter(second.book.id, first.chapters[0].id)
    assert exc_info.value.code == "chapter_not_found"


def test_delete_bookmark_requires_matching_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    first = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="first.epub",
        storage_path="books/first.epub",
    )
    second = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="second.epub",
        storage_path="books/second.epub",
    )
    bookmark = repository.create_bookmark(
        book_id=first.book.id,
        chapter_id=first.chapters[0].id,
        position={"paragraph": 1},
        label=None,
    )

    with pytest.raises(ParseError) as exc_info:
        repository.delete_bookmark(second.book.id, bookmark.id)
    assert exc_info.value.code == "bookmark_not_found"

    with pytest.raises(ParseError) as missing_exc:
        repository.delete_bookmark(first.book.id, "missing")
    assert missing_exc.value.code == "bookmark_not_found"


def test_repository_wraps_sqlite_errors(tmp_path, monkeypatch) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")

    def fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is unavailable")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)

    with pytest.raises(ParseError) as exc_info:
        repository.initialize()
    assert exc_info.value.code == "repository_failed"
