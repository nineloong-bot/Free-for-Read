from time import perf_counter
from urllib.parse import unquote, urlparse

from pydantic import BaseModel

from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode, ParseMetadata, SourceType
from free_for_read.detectors.content_type import detect_source_type
from free_for_read.fetchers.url_fetcher import UrlFetcher
from free_for_read.metadata.builder import build_metadata
from free_for_read.parsers.ebooks import parse_ebook
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
        document = self._parse_detected_content(
            fetched.content,
            source_url=fetched.url,
            source_type=source_type,
        )
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
        document = self._parse_detected_content(
            content,
            source_url=source_url,
            source_type=source_type,
        )
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

    def _parse_detected_content(
        self,
        content: bytes,
        *,
        source_url: str,
        source_type: SourceType,
    ) -> Document:
        if source_type in {SourceType.EPUB, SourceType.FB2, SourceType.FBZ}:
            try:
                return _ebook_document(content, filename=_filename_from_source_url(source_url))
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

        parser = self.registry.get(source_type)
        try:
            return parser.parse(content, source_url=source_url)
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


def _validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ParseError(
            code="invalid_url",
            message="URL must be an absolute HTTP or HTTPS URL.",
            details={"url": url},
        )


def _filename_from_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path = unquote(parsed.path or parsed.netloc)
    return path.rsplit("/", 1)[-1] or "upload"


def _ebook_document(content: bytes, *, filename: str) -> Document:
    ebook = parse_ebook(content, filename=filename)
    root = DocumentNode(type="document")
    for chapter in ebook.chapters:
        root.children.extend(
            _nodes_from_chapter_markdown(chapter.markdown, chapter_title=chapter.title)
        )
    return Document(
        root=root,
        title=ebook.title,
        metadata={
            "author": ebook.author,
            "language": ebook.language,
            "source_type": ebook.source_type.value,
            "chapter_count": ebook.chapter_count,
        },
    )


def _nodes_from_chapter_markdown(markdown: str, *, chapter_title: str) -> list[DocumentNode]:
    nodes: list[DocumentNode] = []
    seen_heading = False
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        text = " ".join(line.strip() for line in paragraph_lines if line.strip())
        if text:
            nodes.append(DocumentNode(type="paragraph", text=text))
        paragraph_lines = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith("#"):
            flush_paragraph()
            marker, _, heading = stripped.partition(" ")
            level = max(1, min(len(marker), 6))
            nodes.append(
                DocumentNode(type="heading", text=heading.strip() or chapter_title, level=level)
            )
            seen_heading = True
        else:
            paragraph_lines.append(stripped)
    flush_paragraph()

    if not seen_heading:
        nodes.insert(0, DocumentNode(type="heading", text=chapter_title, level=1))
    return nodes
