from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, Request

from free_for_read.api.schemas import ParseResponse
from free_for_read.core.errors import ParseError
from free_for_read.core.service import ParseResult


class ParseFileServiceProtocol(Protocol):
    def parse_content(self, content: bytes, *, source_url: str) -> ParseResult:
        ...


def create_parse_file_router(parse_service: ParseFileServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1")

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
            content = await upload.read()
            filename = getattr(upload, "filename", "upload") or "upload"
            source_url = f"file://{filename}"
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
            allowed_roots = [Path.home(), Path.cwd()]
            if not any(str(resolved).startswith(str(root)) for root in allowed_roots):
                raise ParseError(
                    code="invalid_file_path",
                    message="File path is outside allowed directories.",
                    details={"path": file_path},
                )

            if not resolved.exists():
                raise ParseError(
                    code="invalid_file_path",
                    message="File does not exist.",
                    details={"path": file_path},
                )

            content = resolved.read_bytes()
            source_url = f"file://{resolved.as_posix()}"

        return parse_service.parse_content(
            content=content,
            source_url=source_url,
        )

    return router
