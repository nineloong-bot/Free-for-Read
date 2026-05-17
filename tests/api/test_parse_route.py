from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode, ParseMetadata, SourceType
from free_for_read.core.service import ParseResult


class StubService:
    async def parse_url(self, url: str) -> ParseResult:
        return ParseResult(
            markdown="# Hello\n\nWorld",
            document=Document(
                root=DocumentNode(
                    type="document",
                    children=[DocumentNode(type="heading", text="Hello", level=1)],
                ),
                title="Hello",
            ),
            metadata=ParseMetadata(
                title="Hello",
                source_url=url,
                source_type=SourceType.WEB,
                word_count=2,
                processing_ms=5,
                content_length=52,
            ),
        )


class ErrorService:
    async def parse_url(self, url: str) -> ParseResult:
        raise ParseError(
            code="unsupported_source_type",
            message="Unsupported source type: image.",
            details={"source_type": "image"},
        )


def test_parse_route_returns_markdown_document_and_metadata() -> None:
    client = TestClient(create_app(parse_service=StubService()))

    response = client.post("/v1/parse", json={"url": "https://example.com"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"] == "# Hello\n\nWorld"
    assert payload["document"]["title"] == "Hello"
    assert payload["metadata"]["source_type"] == "web"


def test_parse_route_maps_parse_errors_to_error_payload() -> None:
    client = TestClient(create_app(parse_service=ErrorService()))

    response = client.post("/v1/parse", json={"url": "https://example.com/image.png"})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "unsupported_source_type",
            "message": "Unsupported source type: image.",
            "details": {"source_type": "image"},
        }
    }


def test_parse_route_maps_request_validation_errors_to_error_payload() -> None:
    client = TestClient(create_app(parse_service=StubService()))

    response = client.post("/v1/parse", json={"url": "not-a-url"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"
    assert response.json()["error"]["message"] == "Request validation failed."
