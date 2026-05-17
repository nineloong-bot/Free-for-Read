from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from free_for_read.api.routes import ParseServiceProtocol, create_router
from free_for_read.core.errors import ParseError
from free_for_read.core.service import ParseService


def create_app(parse_service: ParseServiceProtocol | None = None) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    service = parse_service or ParseService()
    app.include_router(create_router(service))

    @app.exception_handler(ParseError)
    async def parse_error_handler(_request: Request, exc: ParseError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": exc.to_dict()})

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

    return app
