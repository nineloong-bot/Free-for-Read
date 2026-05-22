import asyncio
import hmac
import os
import signal
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from free_for_read.ai.service import AiService
from free_for_read.api.ai_routes import AiServiceProtocol, create_ai_router
from free_for_read.api.library_routes import LibraryServiceProtocol, create_library_router
from free_for_read.api.parse_file_routes import create_parse_file_router
from free_for_read.api.routes import ParseServiceProtocol, create_router
from free_for_read.core.errors import ParseError
from free_for_read.core.service import ParseService
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def create_app(
    parse_service: ParseServiceProtocol | None = None,
    library_service: LibraryServiceProtocol | None = None,
    ai_service: AiServiceProtocol | None = None,
    storage_root: Path | None = None,
    parse_file_roots: list[Path] | None = None,
    max_file_bytes: int = 25 * 1024 * 1024,
    shutdown_token: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    root = storage_root or Path("storage")
    service = parse_service or ParseService()
    app.include_router(create_router(service))
    app.include_router(
        create_parse_file_router(
            service,
            allowed_roots=parse_file_roots or [Path.cwd(), root],
            max_file_bytes=max_file_bytes,
        )
    )
    library = library_service or LibraryService(
        storage=LocalStorageBackend(root=root),
        repository=SQLiteLibraryRepository(root / "library.sqlite3"),
    )
    library.initialize()
    # NOTE: AI router must be registered BEFORE library router because both
    # mount at /v1/books. If reversed, the library's GET /{book_id} route
    # would capture /search and /{id}/index before the AI router sees them.
    resolved_ai_service = ai_service
    if resolved_ai_service is None and hasattr(library, "repository"):
        resolved_ai_service = AiService(repository=library.repository)  # type: ignore[attr-defined]
    if resolved_ai_service:
        app.include_router(create_ai_router(resolved_ai_service))
    app.include_router(create_library_router(library, max_file_bytes=max_file_bytes))

    @app.exception_handler(ParseError)
    async def parse_error_handler(_request: Request, exc: ParseError) -> JSONResponse:
        not_found_codes = {"book_not_found", "chapter_not_found", "bookmark_not_found"}
        server_error_codes = {"repository_failed", "storage_failed"}
        if exc.code in not_found_codes:
            status_code = 404
        elif exc.code in server_error_codes:
            status_code = 500
        else:
            status_code = 400
        return JSONResponse(status_code=status_code, content={"error": exc.to_dict()})

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_url",
                    "message": "Request validation failed.",
                    "details": {"errors": jsonable_encoder(exc.errors())},
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/shutdown")
    async def shutdown(request: Request):
        supplied = request.headers.get("x-free-for-read-shutdown-token", "")
        if not shutdown_token or not hmac.compare_digest(supplied, shutdown_token):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "shutdown_forbidden",
                        "message": "Shutdown token is missing or invalid.",
                        "details": {},
                    }
                },
            )

        async def _delayed_exit():
            await asyncio.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        asyncio.create_task(_delayed_exit())
        return {"status": "shutting_down"}

    return app
