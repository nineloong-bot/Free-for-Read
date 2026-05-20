import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from free_for_read.core.errors import ParseError
from free_for_read.library.models import (
    Book,
    BookDetail,
    Bookmark,
    Chapter,
    ParsedEbook,
    ReadingProgress,
)


class LibraryRepository(Protocol):
    def initialize(self) -> None:
        raise NotImplementedError

    def create_book(
        self, *, parsed: ParsedEbook, original_filename: str, storage_path: str
    ) -> BookDetail:
        raise NotImplementedError

    def list_books(self, *, limit: int, offset: int) -> list[Book]:
        raise NotImplementedError

    def get_book(self, book_id: str) -> BookDetail:
        raise NotImplementedError

    def list_chapters(self, book_id: str) -> list[Chapter]:
        raise NotImplementedError

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        raise NotImplementedError

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        raise NotImplementedError

    def upsert_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        raise NotImplementedError

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        raise NotImplementedError

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        raise NotImplementedError

    def delete_bookmark(self, book_id: str, bookmark_id: str) -> None:
        raise NotImplementedError


class SQLiteLibraryRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS books (
                      id TEXT PRIMARY KEY,
                      title TEXT NOT NULL,
                      author TEXT,
                      language TEXT,
                      source_type TEXT NOT NULL,
                      original_filename TEXT NOT NULL,
                      storage_path TEXT NOT NULL,
                      cover_path TEXT,
                      word_count INTEGER NOT NULL,
                      chapter_count INTEGER NOT NULL,
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS chapters (
                      id TEXT PRIMARY KEY,
                      book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                      chapter_index INTEGER NOT NULL,
                      title TEXT NOT NULL,
                      markdown TEXT NOT NULL,
                      word_count INTEGER NOT NULL,
                      source_ref TEXT NOT NULL,
                      metadata_json TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS reading_progress (
                      book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
                      chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                      position_json TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS bookmarks (
                      id TEXT PRIMARY KEY,
                      book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                      chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                      position_json TEXT NOT NULL,
                      label TEXT,
                      created_at TEXT NOT NULL
                    );
                    """
                )
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

    def create_book(
        self, *, parsed: ParsedEbook, original_filename: str, storage_path: str
    ) -> BookDetail:
        book_id = f"book_{uuid4().hex}"
        now = self._now()
        chapter_rows = [
            (
                f"chapter_{uuid4().hex}",
                book_id,
                chapter.index,
                chapter.title,
                chapter.markdown,
                chapter.word_count,
                chapter.source_ref,
                self._json_dumps(chapter.metadata),
            )
            for chapter in parsed.chapters
        ]

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO books (
                        id, title, author, language, source_type, original_filename,
                        storage_path, cover_path, word_count, chapter_count, created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        book_id,
                        parsed.title,
                        parsed.author,
                        parsed.language,
                        parsed.source_type.value,
                        original_filename,
                        storage_path,
                        parsed.cover_path,
                        parsed.word_count,
                        parsed.chapter_count,
                        now,
                        now,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO chapters (
                        id, book_id, chapter_index, title, markdown, word_count,
                        source_ref, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    chapter_rows,
                )
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return self.get_book(book_id)

    def list_books(self, *, limit: int, offset: int) -> list[Book]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM books
                    ORDER BY created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return [self._book_from_row(row) for row in rows]

    def get_book(self, book_id: str) -> BookDetail:
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                if row is None:
                    raise self._not_found("book_not_found", "Book was not found", book_id=book_id)
                progress_row = self._progress_row(connection, book_id)
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return BookDetail(
            book=self._book_from_row(row),
            chapters=self.list_chapters(book_id),
            progress=self._progress_from_row(progress_row) if progress_row is not None else None,
        )

    def list_chapters(self, book_id: str) -> list[Chapter]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM chapters
                    WHERE book_id = ?
                    ORDER BY chapter_index ASC, id ASC
                    """,
                    (book_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return [self._chapter_from_row(row) for row in rows]

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM chapters
                    WHERE book_id = ? AND id = ?
                    """,
                    (book_id, chapter_id),
                ).fetchone()
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        if row is None:
            raise self._not_found(
                "chapter_not_found",
                "Chapter was not found",
                book_id=book_id,
                chapter_id=chapter_id,
            )
        return self._chapter_from_row(row)

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        try:
            with self._connect() as connection:
                row = self._progress_row(connection, book_id)
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return self._progress_from_row(row) if row is not None else None

    def upsert_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        self.get_chapter(book_id, chapter_id)
        now = self._now()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO reading_progress (
                        book_id, chapter_id, position_json, updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(book_id) DO UPDATE SET
                        chapter_id = excluded.chapter_id,
                        position_json = excluded.position_json,
                        updated_at = excluded.updated_at
                    """,
                    (book_id, chapter_id, self._json_dumps(position), now),
                )
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        progress = self.get_progress(book_id)
        if progress is None:
            raise ParseError(
                code="repository_failed",
                message="Reading progress could not be loaded after upsert",
                details={"book_id": book_id},
            )
        return progress

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        self.get_chapter(book_id, chapter_id)
        bookmark_id = f"bookmark_{uuid4().hex}"
        now = self._now()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO bookmarks (
                        id, book_id, chapter_id, position_json, label, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (bookmark_id, book_id, chapter_id, self._json_dumps(position), label, now),
                )
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return Bookmark(
            id=bookmark_id,
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            label=label,
            created_at=now,
        )

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM bookmarks
                    WHERE book_id = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (book_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        return [self._bookmark_from_row(row) for row in rows]

    def delete_bookmark(self, book_id: str, bookmark_id: str) -> None:
        try:
            with self._connect() as connection:
                result = connection.execute(
                    "DELETE FROM bookmarks WHERE book_id = ? AND id = ?",
                    (book_id, bookmark_id),
                )
        except sqlite3.Error as exc:
            self._raise_repository_failed(exc)

        if result.rowcount == 0:
            raise self._not_found(
                "bookmark_not_found",
                "Bookmark was not found",
                book_id=book_id,
                bookmark_id=bookmark_id,
            )

    def _connect(self) -> sqlite3.Connection:
        self._ensure_database_parent()
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _ensure_database_parent(self) -> None:
        if str(self.database_path) == ":memory:":
            return
        if self.database_path.parent == Path("."):
            return
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_dumps(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _json_loads(value: str) -> dict[str, Any]:
        loaded = json.loads(value)
        if isinstance(loaded, dict):
            return loaded
        return {}

    @staticmethod
    def _not_found(code: str, message: str, **details: str) -> ParseError:
        return ParseError(code=code, message=message, details=details)

    @staticmethod
    def _raise_repository_failed(exc: sqlite3.Error) -> None:
        raise ParseError(
            code="repository_failed",
            message="Library repository operation failed",
            details={"error": str(exc)},
        ) from exc

    @staticmethod
    def _book_from_row(row: sqlite3.Row) -> Book:
        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            language=row["language"],
            source_type=row["source_type"],
            original_filename=row["original_filename"],
            storage_path=row["storage_path"],
            cover_path=row["cover_path"],
            word_count=row["word_count"],
            chapter_count=row["chapter_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _chapter_from_row(self, row: sqlite3.Row) -> Chapter:
        return Chapter(
            id=row["id"],
            book_id=row["book_id"],
            index=row["chapter_index"],
            title=row["title"],
            markdown=row["markdown"],
            word_count=row["word_count"],
            source_ref=row["source_ref"],
            metadata=self._json_loads(row["metadata_json"]),
        )

    def _progress_from_row(self, row: sqlite3.Row) -> ReadingProgress:
        return ReadingProgress(
            book_id=row["book_id"],
            chapter_id=row["chapter_id"],
            position=self._json_loads(row["position_json"]),
            updated_at=row["updated_at"],
        )

    def _bookmark_from_row(self, row: sqlite3.Row) -> Bookmark:
        return Bookmark(
            id=row["id"],
            book_id=row["book_id"],
            chapter_id=row["chapter_id"],
            position=self._json_loads(row["position_json"]),
            label=row["label"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _progress_row(connection: sqlite3.Connection, book_id: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM reading_progress WHERE book_id = ?",
            (book_id,),
        ).fetchone()
