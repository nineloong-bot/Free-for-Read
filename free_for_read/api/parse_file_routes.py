from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, Request

from free_for_read.api.schemas import ParseResponse
from free_for_read.core.errors import ParseError
from free_for_read.core.service import ParseResult


class ParseFileServiceProtocol(Protocol):
    def parse_content(self, content: bytes, *, source_url: str) -> ParseResult:
        ...


DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024


def create_parse_file_router(
    parse_service: ParseFileServiceProtocol,
    *,
    allowed_roots: list[Path] | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> APIRouter:
    router = APIRouter(prefix="/v1")
    roots = [root.resolve() for root in (allowed_roots or [Path.cwd()])]

    @router.post("/parse/file", response_model=ParseResponse)
    async def parse_file(request: Request):
        content_type = request.headers.get("content-type", "")
        source_url: str
        content: bytes

        if "multipart/form-data" in content_type:
            form = await request.form()
            upload = form.get("file")
            if upload is None:
                raise ParseError(
                    code="invalid_file_path",
                    message="No file field in multipart request.",
                )
            content = await upload.read(max_file_bytes + 1)
            _raise_if_too_large(content_length=len(content), max_file_bytes=max_file_bytes)
            filename = getattr(upload, "filename", "upload") or "upload"
            source_url = f"file:///{filename}"
        else:
            try:
                body = await request.json()
            except Exception:
                raise ParseError(
                    code="invalid_file_path",
                    message="Request body must be valid JSON with a 'path' field.",
                ) from None
            file_path = body.get("path", "") if isinstance(body, dict) else ""

            if not file_path or ".." in Path(file_path).parts:
                raise ParseError(
                    code="invalid_file_path",
                    message="File path is invalid or does not exist.",
                    details={"path": file_path},
                )

            resolved = Path(file_path).resolve()
            if not any(_is_relative_to(resolved, root) for root in roots):
                raise ParseError(
                    code="invalid_file_path",
                    message="File path is outside allowed directories.",
                    details={"path": file_path},
                )

            if not resolved.exists() or not resolved.is_file():
                raise ParseError(
                    code="invalid_file_path",
                    message="File does not exist.",
                    details={"path": file_path},
                )

            _raise_if_too_large(
                content_length=resolved.stat().st_size,
                max_file_bytes=max_file_bytes,
            )
            content = resolved.read_bytes()
            source_url = f"file://{resolved.as_posix()}"

        return parse_service.parse_content(
            content=content,
            source_url=source_url,
        )

    return router


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _raise_if_too_large(*, content_length: int, max_file_bytes: int) -> None:
    if content_length > max_file_bytes:
        raise ParseError(
            code="content_too_large",
            message="Source content is larger than the configured limit.",
            details={"max_bytes": max_file_bytes},
        )
