from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    root = storage_root or Path("storage")
    service = parse_service or ParseService()
    app.include_router(create_router(service))
    app.include_router(create_parse_file_router(service))
    library = library_service or LibraryService(
        storage=LocalStorageBackend(root=root),
        repository=SQLiteLibraryRepository(root / "library.sqlite3"),
    )
    library.initialize()
    # NOTE: AI router must be registered BEFORE library router because both
    # mount at /v1/books. If reversed, the library's GET /{book_id} route
    # would capture /search and /{id}/index before the AI router sees them.
    if ai_service:
        app.include_router(create_ai_router(ai_service))
    app.include_router(create_library_router(library))

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
    async def shutdown():
        import asyncio
        import os
        import signal

        async def _delayed_exit():
            await asyncio.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        asyncio.create_task(_delayed_exit())
        return {"status": "shutting_down"}

    return app
