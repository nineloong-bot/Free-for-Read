from dataclasses import dataclass

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode, SourceType
from free_for_read.core.service import ParseService


@dataclass(frozen=True)
class StubFetchedContent:
    url: str
    content: bytes
    content_type: str | None
    content_length: int | None


class StubFetcher:
    async def fetch(self, url: str) -> StubFetchedContent:
        return StubFetchedContent(
            url=url,
            content=b"<html><body><h1>Hello</h1><p>World</p></body></html>",
            content_type="text/html",
            content_length=52,
        )


class StubParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        return Document(
            root=DocumentNode(
                type="document",
                children=[
                    DocumentNode(type="heading", text="Hello", level=1),
                    DocumentNode(type="paragraph", text="World"),
                ],
            ),
            title="Hello",
        )


class ExplodingParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise ValueError("bad source")


class ParseErrorParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise ParseError(
            code="unsupported_source_type",
            message="Unsupported source type.",
            details={"source_type": "web"},
        )


class StubRegistry:
    def __init__(
        self, parser: StubParser | ExplodingParser | ParseErrorParser | None = None
    ) -> None:
        self.parser = parser or StubParser()

    def get(self, source_type: SourceType) -> StubParser | ExplodingParser | ParseErrorParser:
        assert source_type == SourceType.WEB
        return self.parser


@pytest.mark.asyncio
async def test_parse_url_returns_markdown_document_and_metadata() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry())

    response = await service.parse_url("https://example.com")

    assert response.markdown == "# Hello\n\nWorld"
    assert response.document.title == "Hello"
    assert response.metadata.title == "Hello"
    assert response.metadata.source_type == SourceType.WEB
    assert response.metadata.source_url == "https://example.com"
    assert response.metadata.content_length == 52
    assert response.metadata.processing_ms >= 0


@pytest.mark.asyncio
async def test_parse_url_rejects_non_http_urls() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry())

    with pytest.raises(ParseError) as exc_info:
        await service.parse_url("file:///etc/passwd")

    assert exc_info.value.code == "invalid_url"


@pytest.mark.asyncio
async def test_parse_url_wraps_unexpected_parser_errors_as_parse_failed() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry(ExplodingParser()))

    with pytest.raises(ParseError) as exc_info:
        await service.parse_url("https://example.com")

    assert exc_info.value.code == "parse_failed"
    assert exc_info.value.details == {
        "source_url": "https://example.com",
        "source_type": "web",
    }


@pytest.mark.asyncio
async def test_parse_url_preserves_parser_parse_errors() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry(ParseErrorParser()))

    with pytest.raises(ParseError) as exc_info:
        await service.parse_url("https://example.com")

    assert exc_info.value.code == "unsupported_source_type"


def test_parse_content_reuses_pipeline_for_local_bytes() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry())

    result = service.parse_content(
        content=b"<html>local</html>",
        source_url="file://local.html",
    )

    assert result.markdown == "# Hello\n\nWorld"
    assert result.document.title == "Hello"
    assert result.metadata.source_type == SourceType.WEB
    assert result.metadata.content_length == 18
    assert result.metadata.processing_ms >= 0
