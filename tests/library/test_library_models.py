from datetime import datetime, timezone

from free_for_read.library.models import (
    Book,
    Bookmark,
    Chapter,
    EbookSourceType,
    ParsedChapter,
    ParsedEbook,
    ReadingProgress,
)


def test_parsed_ebook_counts_chapters_and_words() -> None:
    parsed = ParsedEbook(
        title="Example Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.EPUB,
        chapters=[
            ParsedChapter(
                index=0,
                title="Opening",
                markdown="Hello reader.",
                word_count=2,
                source_ref="chapters/opening.xhtml",
            ),
            ParsedChapter(
                index=1,
                title="Second",
                markdown="Another page.",
                word_count=2,
                source_ref="chapters/second.xhtml",
            ),
        ],
    )

    assert parsed.chapter_count == 2
    assert parsed.word_count == 4


def test_library_models_store_progress_and_bookmark_positions() -> None:
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    book = Book(
        id="book_1",
        title="Example Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.FB2,
        original_filename="example.fb2",
        storage_path="books/book_1/source.fb2",
        cover_path=None,
        word_count=10,
        chapter_count=1,
        created_at=now,
        updated_at=now,
    )
    chapter = Chapter(
        id="chapter_1",
        book_id=book.id,
        index=0,
        title="Opening",
        markdown="Hello reader.",
        word_count=2,
        source_ref="body/section[1]",
        metadata={"kind": "section"},
    )
    progress = ReadingProgress(
        book_id=book.id,
        chapter_id=chapter.id,
        position={"paragraph": 3, "offset": 12},
        updated_at=now,
    )
    bookmark = Bookmark(
        id="bookmark_1",
        book_id=book.id,
        chapter_id=chapter.id,
        position={"paragraph": 3, "offset": 12},
        label="Important",
        created_at=now,
    )

    assert book.source_type == EbookSourceType.FB2
    assert chapter.metadata == {"kind": "section"}
    assert progress.position["paragraph"] == 3
    assert bookmark.label == "Important"
