from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EbookSourceType(str, Enum):
    EPUB = "epub"
    FB2 = "fb2"
    FBZ = "fbz"


class ParsedChapter(BaseModel):
    index: int
    title: str
    markdown: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedEbook(BaseModel):
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    chapters: list[ParsedChapter]
    cover_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def word_count(self) -> int:
        return sum(chapter.word_count for chapter in self.chapters)


class Book(BaseModel):
    id: str
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    original_filename: str
    storage_path: str
    cover_path: str | None = None
    word_count: int
    chapter_count: int
    created_at: datetime
    updated_at: datetime


class Chapter(BaseModel):
    id: str
    book_id: str
    index: int
    title: str
    markdown: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReadingProgress(BaseModel):
    book_id: str
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class Bookmark(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None
    created_at: datetime


class BookDetail(BaseModel):
    book: Book
    chapters: list[Chapter]
    progress: ReadingProgress | None = None
