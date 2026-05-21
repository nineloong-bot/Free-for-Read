from time import perf_counter
from urllib.parse import urlparse

from pydantic import BaseModel

from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, ParseMetadata
from free_for_read.detectors.content_type import detect_source_type
from free_for_read.fetchers.url_fetcher import UrlFetcher
from free_for_read.metadata.builder import build_metadata
from free_for_read.parsers.registry import ParserRegistry, default_parser_registry
from free_for_read.renderers.markdown import render_markdown


class ParseResult(BaseModel):
    markdown: str
    document: Document
    metadata: ParseMetadata


class ParseService:
    def __init__(
        self,
        *,
        fetcher: UrlFetcher | None = None,
        registry: ParserRegistry | None = None,
    ) -> None:
        self.fetcher = fetcher or UrlFetcher()
        self.registry = registry or default_parser_registry()

    async def parse_url(self, url: str) -> ParseResult:
        _validate_http_url(url)
        started = perf_counter()
        fetched = await self.fetcher.fetch(url)
        source_type = detect_source_type(
            url=fetched.url,
            content_type=fetched.content_type,
            content=fetched.content,
        )
        parser = self.registry.get(source_type)
        try:
            document = parser.parse(fetched.content, source_url=fetched.url)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(
                code="parse_failed",
                message="Failed to parse source content.",
                details={
                    "source_url": fetched.url,
                    "source_type": source_type.value,
                },
            ) from exc
        markdown = render_markdown(document)
        processing_ms = int((perf_counter() - started) * 1000)
        metadata = build_metadata(
            document=document,
            markdown=markdown,
            source_url=fetched.url,
            source_type=source_type,
            processing_ms=processing_ms,
            content_length=fetched.content_length,
        )
        return ParseResult(markdown=markdown, document=document, metadata=metadata)

    def parse_content(self, content: bytes, *, source_url: str) -> ParseResult:
        source_type = detect_source_type(
            url=source_url,
            content_type=None,
            content=content,
        )
        parser = self.registry.get(source_type)
        try:
            document = parser.parse(content, source_url=source_url)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(
                code="parse_failed",
                message="Failed to parse source content.",
                details={
                    "source_url": source_url,
                    "source_type": source_type.value,
                },
            ) from exc
        markdown = render_markdown(document)
        metadata = build_metadata(
            document=document,
            markdown=markdown,
            source_url=source_url,
            source_type=source_type,
            processing_ms=0,
            content_length=len(content),
        )
        return ParseResult(markdown=markdown, document=document, metadata=metadata)


def _validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ParseError(
            code="invalid_url",
            message="URL must be an absolute HTTP or HTTPS URL.",
            details={"url": url},
        )
