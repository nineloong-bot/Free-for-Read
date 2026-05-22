from typing import Annotated, Any, Protocol

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse
from starlette import status

from free_for_read.api.library_schemas import (
    BookDetailResponse,
    BookListResponse,
    BookmarkListResponse,
    BookmarkRequest,
    BookmarkResponse,
    ChapterListResponse,
    ChapterResponse,
    ProgressRequest,
    ProgressResponse,
)
from free_for_read.library.models import Book, BookDetail, Bookmark, Chapter, ReadingProgress

DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024


class LibraryServiceProtocol(Protocol):
    def initialize(self) -> None:
        raise NotImplementedError

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        raise NotImplementedError

    def get_source_path(self, book_id: str):
        raise NotImplementedError

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        raise NotImplementedError

    def get_book(self, book_id: str) -> BookDetail:
        raise NotImplementedError

    def list_chapters(self, book_id: str) -> list[Chapter]:
        raise NotImplementedError

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        raise NotImplementedError

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        raise NotImplementedError

    def update_progress(
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

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        raise NotImplementedError

    def delete_book(self, book_id: str) -> None:
        raise NotImplementedError


def create_library_router(
    service: LibraryServiceProtocol,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> APIRouter:
    router = APIRouter(prefix="/v1/books")

    @router.post("/import", response_model=BookDetailResponse)
    async def import_book(file: Annotated[UploadFile, File(...)]) -> BookDetail:
        content = await file.read(max_file_bytes + 1)
        if len(content) > max_file_bytes:
            from free_for_read.core.errors import ParseError

            raise ParseError(
                code="content_too_large",
                message="Source content is larger than the configured limit.",
                details={"max_bytes": max_file_bytes},
            )
        return service.import_book(filename=file.filename or "upload", content=content)

    @router.get("", response_model=BookListResponse)
    def list_books(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        return {
            "items": service.list_books(limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    @router.get("/{book_id}", response_model=BookDetailResponse)
    def get_book(book_id: str) -> BookDetail:
        return service.get_book(book_id)

    @router.get("/{book_id}/source")
    def get_book_source(book_id: str) -> FileResponse:
        source_path = service.get_source_path(book_id)
        return FileResponse(source_path)

    @router.get("/{book_id}/chapters", response_model=ChapterListResponse)
    def list_chapters(book_id: str) -> dict[str, list[Chapter]]:
        return {"items": service.list_chapters(book_id)}

    @router.get("/{book_id}/chapters/{chapter_id}", response_model=ChapterResponse)
    def get_chapter(book_id: str, chapter_id: str) -> dict[str, object]:
        chapters = service.list_chapters(book_id)
        chapter = service.get_chapter(book_id, chapter_id)
        chapter_ids = [item.id for item in chapters]
        current_index = chapter_ids.index(chapter.id)
        previous_id = chapter_ids[current_index - 1] if current_index > 0 else None
        next_id = (
            chapter_ids[current_index + 1]
            if current_index + 1 < len(chapter_ids)
            else None
        )
        return {
            **chapter.model_dump(),
            "previous_chapter_id": previous_id,
            "next_chapter_id": next_id,
        }

    @router.get("/{book_id}/progress", response_model=ProgressResponse | None)
    def get_progress(book_id: str) -> ReadingProgress | None:
        return service.get_progress(book_id)

    @router.put("/{book_id}/progress", response_model=ProgressResponse)
    def update_progress(book_id: str, request: ProgressRequest) -> ReadingProgress:
        return service.update_progress(
            book_id=book_id,
            chapter_id=request.chapter_id,
            position=request.position,
        )

    @router.post("/{book_id}/bookmarks", response_model=BookmarkResponse)
    def create_bookmark(book_id: str, request: BookmarkRequest) -> Bookmark:
        return service.create_bookmark(
            book_id=book_id,
            chapter_id=request.chapter_id,
            position=request.position,
            label=request.label,
        )

    @router.get("/{book_id}/bookmarks", response_model=BookmarkListResponse)
    def list_bookmarks(book_id: str) -> dict[str, list[Bookmark]]:
        return {"items": service.list_bookmarks(book_id)}

    @router.delete(
        "/{book_id}/bookmarks/{bookmark_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_bookmark(book_id: str, bookmark_id: str) -> None:
        service.delete_bookmark(book_id=book_id, bookmark_id=bookmark_id)

    @router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book(book_id: str) -> None:
        service.delete_book(book_id)

    return router
