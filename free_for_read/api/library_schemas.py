from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from free_for_read.library.models import EbookSourceType


class BookResponse(BaseModel):
    id: str
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    original_filename: str
    cover_path: str | None = None
    word_count: int
    chapter_count: int
    created_at: datetime
    updated_at: datetime


class ChapterSummaryResponse(BaseModel):
    id: str
    book_id: str
    index: int
    title: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChapterResponse(ChapterSummaryResponse):
    markdown: str
    previous_chapter_id: str | None = None
    next_chapter_id: str | None = None


class ProgressRequest(BaseModel):
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)


class ProgressResponse(BaseModel):
    book_id: str
    chapter_id: str
    position: dict[str, Any]
    updated_at: datetime


class BookmarkRequest(BaseModel):
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None


class BookmarkResponse(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    position: dict[str, Any]
    label: str | None = None
    created_at: datetime


class BookDetailResponse(BaseModel):
    book: BookResponse
    chapters: list[ChapterSummaryResponse]
    progress: ProgressResponse | None = None


class BookListResponse(BaseModel):
    items: list[BookResponse]
    limit: int
    offset: int


class ChapterListResponse(BaseModel):
    items: list[ChapterSummaryResponse]


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
