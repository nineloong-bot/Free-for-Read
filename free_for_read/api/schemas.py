from typing import Any

from pydantic import BaseModel, HttpUrl

from free_for_read.core.models import Document, ParseMetadata


class ParseRequest(BaseModel):
    url: HttpUrl


class ParseResponse(BaseModel):
    markdown: str
    document: Document
    metadata: ParseMetadata


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    error: ErrorBody
