from typing import Protocol

from fastapi import APIRouter

from free_for_read.api.schemas import ParseRequest, ParseResponse
from free_for_read.core.service import ParseResult


class ParseServiceProtocol(Protocol):
    async def parse_url(self, url: str) -> ParseResult:
        raise NotImplementedError


def create_router(parse_service: ParseServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post("/parse", response_model=ParseResponse)
    async def parse(request: ParseRequest) -> ParseResult:
        return await parse_service.parse_url(str(request.url))

    return router
