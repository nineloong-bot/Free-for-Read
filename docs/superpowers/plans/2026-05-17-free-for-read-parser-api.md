# Free for Read Parser API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first stateless FastAPI parsing API that accepts a remote URL and returns clean Markdown, a unified document AST, and metadata.

**Architecture:** FastAPI validates and serializes requests at the boundary. A core parse service fetches URL content, detects source type, selects an isolated parser, renders Markdown from the unified AST, and builds metadata. Each parser converts one source family into the same `Document` and `DocumentNode` model.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2, httpx, trafilatura, beautifulsoup4, pypdf, python-docx, python-pptx, pytest, pytest-httpx, ruff.

---

## File Structure

- Create `pyproject.toml`: project metadata, runtime dependencies, pytest and ruff configuration.
- Create `README.md`: local setup and API usage.
- Create `free_for_read/__init__.py`: package marker and version.
- Create `free_for_read/api/app.py`: FastAPI app factory.
- Create `free_for_read/api/routes.py`: `/v1/parse` route and error mapping.
- Create `free_for_read/api/schemas.py`: Pydantic request, response, and error schemas.
- Create `free_for_read/core/models.py`: source-neutral document model and metadata model.
- Create `free_for_read/core/errors.py`: typed domain errors.
- Create `free_for_read/core/service.py`: parse orchestration.
- Create `free_for_read/fetchers/url_fetcher.py`: URL fetcher with timeout, max size, redirects, and User-Agent.
- Create `free_for_read/detectors/content_type.py`: source type detection from URL, headers, and content sniffing.
- Create `free_for_read/parsers/base.py`: parser protocol.
- Create `free_for_read/parsers/registry.py`: source type to parser resolution.
- Create `free_for_read/parsers/web.py`: web page parser.
- Create `free_for_read/parsers/pdf.py`: PDF parser.
- Create `free_for_read/parsers/office.py`: Word and PowerPoint parsers.
- Create `free_for_read/parsers/image.py`: unsupported image parser stub.
- Create `free_for_read/renderers/markdown.py`: AST to Markdown renderer.
- Create `free_for_read/metadata/builder.py`: metadata construction and word counting.
- Create `tests/` files alongside each behavior.

## Task 1: Project Skeleton And App Factory

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `free_for_read/__init__.py`
- Create: `free_for_read/api/__init__.py`
- Create: `free_for_read/api/app.py`
- Test: `tests/api/test_app.py`

- [ ] **Step 1: Write the failing app factory test**

Create `tests/api/test_app.py`:

```python
from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def test_create_app_exposes_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_app.py::test_create_app_exposes_health_endpoint -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'free_for_read'`.

- [ ] **Step 3: Add project config and minimal app factory**

Create `pyproject.toml`:

```toml
[project]
name = "free-for-read"
version = "0.1.0"
description = "A document and content parsing engine for clean Markdown, LLM, and RAG workflows."
requires-python = ">=3.10"
dependencies = [
  "beautifulsoup4>=4.12.0",
  "fastapi>=0.111.0",
  "httpx>=0.27.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.2.0",
  "pypdf>=4.2.0",
  "python-docx>=1.1.0",
  "python-pptx>=0.6.23",
  "trafilatura>=1.9.0",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-asyncio>=0.23.0",
  "pytest-httpx>=0.30.0",
  "ruff>=0.4.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Create `README.md`:

````markdown
# Free for Read

Free for Read is a backend parsing API that turns remote web pages and documents into clean Markdown, a unified document AST, and metadata for LLM and RAG workflows.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn free_for_read.api.app:create_app --factory --reload
```

## API

```http
POST /v1/parse
Content-Type: application/json

{
  "url": "https://example.com/book.pdf"
}
```
````

Create `free_for_read/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `free_for_read/api/__init__.py`:

```python
```

Create `free_for_read/api/app.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_app.py::test_create_app_exposes_health_endpoint -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md free_for_read tests/api/test_app.py
git commit -m "feat: add project skeleton"
```

## Task 2: Core Document Models, Markdown Renderer, And Metadata Builder

**Files:**
- Create: `free_for_read/core/__init__.py`
- Create: `free_for_read/core/models.py`
- Create: `free_for_read/renderers/__init__.py`
- Create: `free_for_read/renderers/markdown.py`
- Create: `free_for_read/metadata/__init__.py`
- Create: `free_for_read/metadata/builder.py`
- Test: `tests/core/test_models.py`
- Test: `tests/renderers/test_markdown.py`
- Test: `tests/metadata/test_builder.py`

- [ ] **Step 1: Write failing tests for models, rendering, and metadata**

Create `tests/core/test_models.py`:

```python
from free_for_read.core.models import Document, DocumentNode


def test_document_node_serializes_nested_children() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(type="heading", text="Chapter 1", level=1),
                DocumentNode(type="paragraph", text="The first paragraph."),
            ],
        ),
        title="Novel",
    )

    payload = document.model_dump()

    assert payload["title"] == "Novel"
    assert payload["root"]["children"][0]["type"] == "heading"
    assert payload["root"]["children"][0]["level"] == 1
```

Create `tests/renderers/test_markdown.py`:

```python
from free_for_read.core.models import Document, DocumentNode
from free_for_read.renderers.markdown import render_markdown


def test_render_markdown_handles_headings_paragraphs_lists_tables_and_slides() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(type="heading", text="Title", level=1),
                DocumentNode(type="paragraph", text="Intro text."),
                DocumentNode(
                    type="list",
                    children=[
                        DocumentNode(type="list_item", text="First"),
                        DocumentNode(type="list_item", text="Second"),
                    ],
                ),
                DocumentNode(
                    type="table",
                    children=[
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="A"),
                                DocumentNode(type="table_cell", text="B"),
                            ],
                        ),
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="1"),
                                DocumentNode(type="table_cell", text="2"),
                            ],
                        ),
                    ],
                ),
                DocumentNode(type="slide", metadata={"slide_number": 2}, children=[
                    DocumentNode(type="heading", text="Slide Title", level=2),
                ]),
            ],
        )
    )

    assert render_markdown(document) == (
        "# Title\n\n"
        "Intro text.\n\n"
        "- First\n"
        "- Second\n\n"
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n\n"
        "---\n\n"
        "## Slide 2\n\n"
        "## Slide Title"
    )
```

Create `tests/metadata/test_builder.py`:

```python
from free_for_read.core.models import Document, DocumentNode, SourceType
from free_for_read.metadata.builder import build_metadata


def test_build_metadata_counts_words_and_preserves_source_fields() -> None:
    document = Document(
        root=DocumentNode(type="document"),
        title="A Tale",
    )

    metadata = build_metadata(
        document=document,
        markdown="# A Tale\n\nHello clean world.",
        source_url="https://example.com/tale.html",
        source_type=SourceType.WEB,
        processing_ms=42,
        content_length=128,
    )

    assert metadata.title == "A Tale"
    assert metadata.source_url == "https://example.com/tale.html"
    assert metadata.source_type == SourceType.WEB
    assert metadata.word_count == 4
    assert metadata.processing_ms == 42
    assert metadata.content_length == 128
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_models.py tests/renderers/test_markdown.py tests/metadata/test_builder.py -v`

Expected: FAIL with import errors for missing modules.

- [ ] **Step 3: Implement models, renderer, and metadata builder**

Create `free_for_read/core/__init__.py`:

```python
```

Create `free_for_read/core/models.py`:

```python
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    WEB = "web"
    PDF = "pdf"
    WORD = "word"
    POWERPOINT = "powerpoint"
    IMAGE = "image"


NodeType = Literal[
    "document",
    "heading",
    "paragraph",
    "list",
    "list_item",
    "table",
    "table_row",
    "table_cell",
    "image",
    "page_break",
    "slide",
]


class DocumentNode(BaseModel):
    type: NodeType
    text: str | None = None
    level: int | None = None
    children: list["DocumentNode"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    root: DocumentNode
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseMetadata(BaseModel):
    title: str | None = None
    source_url: str
    source_type: SourceType
    word_count: int
    processing_ms: int
    content_length: int | None = None
```

Create `free_for_read/renderers/__init__.py`:

```python
```

Create `free_for_read/renderers/markdown.py`:

```python
from free_for_read.core.models import Document, DocumentNode


def render_markdown(document: Document) -> str:
    return "\n\n".join(
        block for block in (_render_node(child) for child in document.root.children) if block
    ).strip()


def _render_node(node: DocumentNode) -> str:
    if node.type == "heading":
        level = max(1, min(node.level or 1, 6))
        return f"{'#' * level} {_clean(node.text)}"
    if node.type == "paragraph":
        return _clean(node.text)
    if node.type == "list":
        return "\n".join(f"- {_clean(child.text)}" for child in node.children)
    if node.type == "table":
        return _render_table(node)
    if node.type == "page_break":
        return "---"
    if node.type == "slide":
        slide_number = node.metadata.get("slide_number")
        title = f"## Slide {slide_number}" if slide_number is not None else "## Slide"
        body = "\n\n".join(
            block for block in (_render_node(child) for child in node.children) if block
        )
        return f"{title}\n\n{body}".strip()
    if node.children:
        return "\n\n".join(block for block in (_render_node(child) for child in node.children) if block)
    return _clean(node.text)


def _render_table(node: DocumentNode) -> str:
    rows = [[_clean(cell.text) for cell in row.children] for row in node.children]
    if not rows:
        return ""
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())
```

Create `free_for_read/metadata/__init__.py`:

```python
```

Create `free_for_read/metadata/builder.py`:

```python
import re

from free_for_read.core.models import Document, ParseMetadata, SourceType


WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def build_metadata(
    *,
    document: Document,
    markdown: str,
    source_url: str,
    source_type: SourceType,
    processing_ms: int,
    content_length: int | None,
) -> ParseMetadata:
    return ParseMetadata(
        title=document.title,
        source_url=source_url,
        source_type=source_type,
        word_count=len(WORD_RE.findall(markdown)),
        processing_ms=processing_ms,
        content_length=content_length,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_models.py tests/renderers/test_markdown.py tests/metadata/test_builder.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/core free_for_read/renderers free_for_read/metadata tests/core tests/renderers tests/metadata
git commit -m "feat: add document model and markdown rendering"
```

## Task 3: Domain Errors, Content Type Detection, And URL Fetching

**Files:**
- Create: `free_for_read/core/errors.py`
- Create: `free_for_read/detectors/__init__.py`
- Create: `free_for_read/detectors/content_type.py`
- Create: `free_for_read/fetchers/__init__.py`
- Create: `free_for_read/fetchers/url_fetcher.py`
- Test: `tests/core/test_errors.py`
- Test: `tests/detectors/test_content_type.py`
- Test: `tests/fetchers/test_url_fetcher.py`

- [ ] **Step 1: Write failing tests for errors, detection, and fetching**

Create `tests/core/test_errors.py`:

```python
from free_for_read.core.errors import ParseError


def test_parse_error_serializes_code_message_and_details() -> None:
    error = ParseError(
        code="fetch_failed",
        message="Unable to fetch URL.",
        details={"url": "https://example.com"},
    )

    assert error.to_dict() == {
        "code": "fetch_failed",
        "message": "Unable to fetch URL.",
        "details": {"url": "https://example.com"},
    }
```

Create `tests/detectors/test_content_type.py`:

```python
from free_for_read.core.models import SourceType
from free_for_read.detectors.content_type import detect_source_type


def test_detects_pdf_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/file",
        content_type="application/pdf",
        content=b"%PDF-1.7",
    ) == SourceType.PDF


def test_detects_word_from_extension() -> None:
    assert detect_source_type(
        url="https://example.com/file.docx",
        content_type="application/octet-stream",
        content=b"PK\x03\x04",
    ) == SourceType.WORD


def test_detects_powerpoint_from_extension() -> None:
    assert detect_source_type(
        url="https://example.com/slides.pptx",
        content_type="application/octet-stream",
        content=b"PK\x03\x04",
    ) == SourceType.POWERPOINT


def test_detects_image_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/image",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\n",
    ) == SourceType.IMAGE


def test_defaults_html_to_web() -> None:
    assert detect_source_type(
        url="https://example.com/article",
        content_type="text/html; charset=utf-8",
        content=b"<html><body>Article</body></html>",
    ) == SourceType.WEB
```

Create `tests/fetchers/test_url_fetcher.py`:

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock

from free_for_read.core.errors import ParseError
from free_for_read.fetchers.url_fetcher import UrlFetcher


@pytest.mark.asyncio
async def test_fetcher_returns_content_headers_and_final_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/doc.html",
        content=b"<html>ok</html>",
        headers={"content-type": "text/html", "content-length": "15"},
    )
    fetcher = UrlFetcher()

    result = await fetcher.fetch("https://example.com/doc.html")

    assert result.url == "https://example.com/doc.html"
    assert result.content == b"<html>ok</html>"
    assert result.content_type == "text/html"
    assert result.content_length == 15


@pytest.mark.asyncio
async def test_fetcher_rejects_content_larger_than_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        content=b"0123456789",
        headers={"content-type": "application/pdf", "content-length": "10"},
    )
    fetcher = UrlFetcher(max_bytes=5)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"


@pytest.mark.asyncio
async def test_fetcher_maps_timeout_to_parse_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.TimeoutException("boom"))
    fetcher = UrlFetcher()

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/slow")

    assert exc_info.value.code == "fetch_timeout"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_errors.py tests/detectors/test_content_type.py tests/fetchers/test_url_fetcher.py -v`

Expected: FAIL with import errors for missing modules.

- [ ] **Step 3: Implement errors, detector, and fetcher**

Create `free_for_read/core/errors.py`:

```python
from typing import Any


class ParseError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
```

Create `free_for_read/detectors/__init__.py`:

```python
```

Create `free_for_read/detectors/content_type.py`:

```python
from pathlib import PurePosixPath
from urllib.parse import urlparse

from free_for_read.core.models import SourceType


def detect_source_type(*, url: str, content_type: str | None, content: bytes) -> SourceType:
    normalized = (content_type or "").split(";")[0].strip().lower()
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()

    if normalized == "application/pdf" or content.startswith(b"%PDF"):
        return SourceType.PDF
    if suffix == ".docx" or normalized in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return SourceType.WORD
    if suffix == ".pptx" or normalized in {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    }:
        return SourceType.POWERPOINT
    if normalized.startswith("image/"):
        return SourceType.IMAGE
    if normalized in {"text/html", "application/xhtml+xml"} or b"<html" in content[:512].lower():
        return SourceType.WEB
    return SourceType.WEB
```

Create `free_for_read/fetchers/__init__.py`:

```python
```

Create `free_for_read/fetchers/url_fetcher.py`:

```python
from dataclasses import dataclass

import httpx

from free_for_read.core.errors import ParseError


@dataclass(frozen=True)
class FetchedContent:
    url: str
    content: bytes
    content_type: str | None
    content_length: int | None


class UrlFetcher:
    def __init__(self, *, timeout_seconds: float = 20.0, max_bytes: int = 25 * 1024 * 1024) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    async def fetch(self, url: str) -> FetchedContent:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "FreeForRead/0.1"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ParseError(
                code="fetch_timeout",
                message="Timed out while fetching source URL.",
                details={"url": url},
            ) from exc
        except httpx.HTTPError as exc:
            raise ParseError(
                code="fetch_failed",
                message="Failed to fetch source URL.",
                details={"url": url},
            ) from exc

        content_length = _parse_content_length(response.headers.get("content-length"))
        if content_length is not None and content_length > self.max_bytes:
            raise ParseError(
                code="content_too_large",
                message="Source content is larger than the configured limit.",
                details={"url": url, "max_bytes": self.max_bytes},
            )
        if len(response.content) > self.max_bytes:
            raise ParseError(
                code="content_too_large",
                message="Source content is larger than the configured limit.",
                details={"url": url, "max_bytes": self.max_bytes},
            )

        return FetchedContent(
            url=str(response.url),
            content=response.content,
            content_type=response.headers.get("content-type"),
            content_length=content_length,
        )


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_errors.py tests/detectors/test_content_type.py tests/fetchers/test_url_fetcher.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/core/errors.py free_for_read/detectors free_for_read/fetchers tests/core/test_errors.py tests/detectors tests/fetchers
git commit -m "feat: add fetching and type detection"
```

## Task 4: Parser Protocol, Registry, Web Parser, And Image Unsupported Parser

**Files:**
- Create: `free_for_read/parsers/__init__.py`
- Create: `free_for_read/parsers/base.py`
- Create: `free_for_read/parsers/registry.py`
- Create: `free_for_read/parsers/web.py`
- Create: `free_for_read/parsers/image.py`
- Test: `tests/parsers/test_registry.py`
- Test: `tests/parsers/test_web.py`
- Test: `tests/parsers/test_image.py`

- [ ] **Step 1: Write failing parser tests**

Create `tests/parsers/test_registry.py`:

```python
import pytest

from free_for_read.core.errors import ParseError
from free_for_read.core.models import SourceType
from free_for_read.parsers.registry import default_parser_registry


def test_default_registry_returns_parser_for_web() -> None:
    registry = default_parser_registry()

    parser = registry.get(SourceType.WEB)

    assert parser.source_type == SourceType.WEB


def test_registry_raises_for_unregistered_source_type() -> None:
    registry = default_parser_registry(include_images=False)

    with pytest.raises(ParseError) as exc_info:
        registry.get(SourceType.IMAGE)

    assert exc_info.value.code == "unsupported_source_type"
```

Create `tests/parsers/test_web.py`:

```python
from free_for_read.parsers.web import WebParser
from free_for_read.renderers.markdown import render_markdown


def test_web_parser_extracts_title_headings_and_paragraphs() -> None:
    html = b"""
    <html>
      <head><title>Ignored Browser Title</title></head>
      <body>
        <nav>Navigation</nav>
        <main>
          <article>
            <h1>Clean Article</h1>
            <p>Hello <strong>reader</strong>.</p>
            <h2>Part One</h2>
            <p>Useful text.</p>
          </article>
        </main>
      </body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/article")

    assert document.title == "Clean Article"
    assert render_markdown(document) == "# Clean Article\n\nHello reader.\n\n## Part One\n\nUseful text."
```

Create `tests/parsers/test_image.py`:

```python
import pytest

from free_for_read.core.errors import ParseError
from free_for_read.parsers.image import ImageParser


def test_image_parser_reports_unsupported_source_type() -> None:
    with pytest.raises(ParseError) as exc_info:
        ImageParser().parse(b"image-bytes", source_url="https://example.com/image.png")

    assert exc_info.value.code == "unsupported_source_type"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/parsers/test_registry.py tests/parsers/test_web.py tests/parsers/test_image.py -v`

Expected: FAIL with import errors for missing parser modules.

- [ ] **Step 3: Implement parser protocol, registry, web parser, and image parser**

Create `free_for_read/parsers/__init__.py`:

```python
```

Create `free_for_read/parsers/base.py`:

```python
from typing import Protocol

from free_for_read.core.models import Document, SourceType


class Parser(Protocol):
    source_type: SourceType

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise NotImplementedError
```

Create `free_for_read/parsers/registry.py`:

```python
from free_for_read.core.errors import ParseError
from free_for_read.core.models import SourceType
from free_for_read.parsers.base import Parser
from free_for_read.parsers.image import ImageParser
from free_for_read.parsers.web import WebParser


class ParserRegistry:
    def __init__(self, parsers: list[Parser]) -> None:
        self._parsers = {parser.source_type: parser for parser in parsers}

    def get(self, source_type: SourceType) -> Parser:
        parser = self._parsers.get(source_type)
        if parser is None:
            raise ParseError(
                code="unsupported_source_type",
                message=f"Unsupported source type: {source_type.value}.",
                details={"source_type": source_type.value},
            )
        return parser


def default_parser_registry(*, include_images: bool = True) -> ParserRegistry:
    parsers: list[Parser] = [WebParser()]
    if include_images:
        parsers.append(ImageParser())
    return ParserRegistry(parsers)
```

Create `free_for_read/parsers/web.py`:

```python
from bs4 import BeautifulSoup
import trafilatura

from free_for_read.core.models import Document, DocumentNode, SourceType


class WebParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        html = content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        root = DocumentNode(type="document")
        article = soup.find("article") or soup.find("main") or soup.body or soup

        for tag in article.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            if tag.name and tag.name.startswith("h"):
                root.children.append(
                    DocumentNode(type="heading", text=text, level=int(tag.name[1]))
                )
            else:
                root.children.append(DocumentNode(type="paragraph", text=text))

        if not root.children:
            extracted = trafilatura.extract(html, url=source_url, output_format="txt") or ""
            root.children.extend(
                DocumentNode(type="paragraph", text=line.strip())
                for line in extracted.splitlines()
                if line.strip()
            )

        title = _first_heading(root) or _html_title(soup)
        return Document(root=root, title=title)


def _first_heading(root: DocumentNode) -> str | None:
    for child in root.children:
        if child.type == "heading" and child.text:
            return child.text
    return None


def _html_title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None
```

Create `free_for_read/parsers/image.py`:

```python
from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, SourceType


class ImageParser:
    source_type = SourceType.IMAGE

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise ParseError(
            code="unsupported_source_type",
            message="Image parsing requires OCR support, which is not enabled in this version.",
            details={"source_url": source_url, "source_type": self.source_type.value},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/parsers/test_registry.py tests/parsers/test_web.py tests/parsers/test_image.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/parsers tests/parsers
git commit -m "feat: add parser registry and web parser"
```

## Task 5: PDF, Word, And PowerPoint Parsers

**Files:**
- Create: `free_for_read/parsers/pdf.py`
- Create: `free_for_read/parsers/office.py`
- Modify: `free_for_read/parsers/registry.py`
- Test: `tests/parsers/test_pdf.py`
- Test: `tests/parsers/test_office.py`
- Test: `tests/parsers/test_registry.py`

- [ ] **Step 1: Write failing parser tests for PDF and Office formats**

Create `tests/parsers/test_pdf.py`:

```python
from io import BytesIO

from pypdf import PdfWriter

from free_for_read.parsers.pdf import PdfParser
from free_for_read.renderers.markdown import render_markdown


def test_pdf_parser_extracts_page_text_and_page_breaks() -> None:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "Tiny PDF"})
    writer.write(buffer)

    document = PdfParser().parse(buffer.getvalue(), source_url="https://example.com/tiny.pdf")

    assert document.title == "Tiny PDF"
    assert render_markdown(document) == "---"
```

Create `tests/parsers/test_office.py`:

```python
from io import BytesIO

from docx import Document as DocxDocument
from pptx import Presentation

from free_for_read.parsers.office import PowerPointParser, WordParser
from free_for_read.renderers.markdown import render_markdown


def test_word_parser_maps_headings_and_paragraphs() -> None:
    source = DocxDocument()
    source.add_heading("Chapter One", level=1)
    source.add_paragraph("Once upon a time.")
    buffer = BytesIO()
    source.save(buffer)

    document = WordParser().parse(buffer.getvalue(), source_url="https://example.com/book.docx")

    assert document.title == "Chapter One"
    assert render_markdown(document) == "# Chapter One\n\nOnce upon a time."


def test_powerpoint_parser_maps_slides_and_text() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    slide.shapes.title.text = "Opening"
    slide.placeholders[1].text = "Welcome readers"
    buffer = BytesIO()
    presentation.save(buffer)

    document = PowerPointParser().parse(
        buffer.getvalue(),
        source_url="https://example.com/deck.pptx",
    )

    assert document.title == "Opening"
    assert render_markdown(document) == "## Slide 1\n\n# Opening\n\nWelcome readers"
```

Modify `tests/parsers/test_registry.py` by extending `test_default_registry_returns_parser_for_web`:

```python
def test_default_registry_returns_parsers_for_supported_source_types() -> None:
    registry = default_parser_registry()

    assert registry.get(SourceType.WEB).source_type == SourceType.WEB
    assert registry.get(SourceType.PDF).source_type == SourceType.PDF
    assert registry.get(SourceType.WORD).source_type == SourceType.WORD
    assert registry.get(SourceType.POWERPOINT).source_type == SourceType.POWERPOINT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/parsers/test_pdf.py tests/parsers/test_office.py tests/parsers/test_registry.py -v`

Expected: FAIL because `free_for_read.parsers.pdf` and `free_for_read.parsers.office` do not exist and the registry lacks PDF and Office parsers.

- [ ] **Step 3: Implement PDF and Office parsers and register them**

Create `free_for_read/parsers/pdf.py`:

```python
from io import BytesIO

from pypdf import PdfReader

from free_for_read.core.models import Document, DocumentNode, SourceType


class PdfParser:
    source_type = SourceType.PDF

    def parse(self, content: bytes, *, source_url: str) -> Document:
        reader = PdfReader(BytesIO(content))
        root = DocumentNode(type="document")
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for paragraph in _paragraphs(text):
                root.children.append(
                    DocumentNode(
                        type="paragraph",
                        text=paragraph,
                        metadata={"page_number": index},
                    )
                )
            root.children.append(DocumentNode(type="page_break", metadata={"page_number": index}))
        return Document(root=root, title=_title(reader))


def _paragraphs(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _title(reader: PdfReader) -> str | None:
    metadata = reader.metadata
    if metadata and metadata.title:
        return str(metadata.title)
    return None
```

Create `free_for_read/parsers/office.py`:

```python
from io import BytesIO

from docx import Document as DocxDocument
from pptx import Presentation

from free_for_read.core.models import Document, DocumentNode, SourceType


class WordParser:
    source_type = SourceType.WORD

    def parse(self, content: bytes, *, source_url: str) -> Document:
        source = DocxDocument(BytesIO(content))
        root = DocumentNode(type="document")
        for paragraph in source.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            if paragraph.style and paragraph.style.name.startswith("Heading"):
                root.children.append(DocumentNode(type="heading", text=text, level=_heading_level(paragraph.style.name)))
            else:
                root.children.append(DocumentNode(type="paragraph", text=text))
        return Document(root=root, title=_first_heading(root))


class PowerPointParser:
    source_type = SourceType.POWERPOINT

    def parse(self, content: bytes, *, source_url: str) -> Document:
        presentation = Presentation(BytesIO(content))
        root = DocumentNode(type="document")
        for slide_number, slide in enumerate(presentation.slides, start=1):
            slide_node = DocumentNode(type="slide", metadata={"slide_number": slide_number})
            for shape in slide.shapes:
                if not hasattr(shape, "text"):
                    continue
                text = shape.text.strip()
                if not text:
                    continue
                if shape == slide.shapes.title:
                    slide_node.children.append(DocumentNode(type="heading", text=text, level=1))
                else:
                    slide_node.children.append(DocumentNode(type="paragraph", text=text))
            root.children.append(slide_node)
        return Document(root=root, title=_first_slide_heading(root))


def _heading_level(style_name: str) -> int:
    try:
        return int(style_name.rsplit(" ", 1)[-1])
    except ValueError:
        return 1


def _first_heading(root: DocumentNode) -> str | None:
    for child in root.children:
        if child.type == "heading" and child.text:
            return child.text
    return None


def _first_slide_heading(root: DocumentNode) -> str | None:
    for slide in root.children:
        for child in slide.children:
            if child.type == "heading" and child.text:
                return child.text
    return None
```

Modify `free_for_read/parsers/registry.py`:

```python
from free_for_read.core.errors import ParseError
from free_for_read.core.models import SourceType
from free_for_read.parsers.base import Parser
from free_for_read.parsers.image import ImageParser
from free_for_read.parsers.office import PowerPointParser, WordParser
from free_for_read.parsers.pdf import PdfParser
from free_for_read.parsers.web import WebParser


class ParserRegistry:
    def __init__(self, parsers: list[Parser]) -> None:
        self._parsers = {parser.source_type: parser for parser in parsers}

    def get(self, source_type: SourceType) -> Parser:
        parser = self._parsers.get(source_type)
        if parser is None:
            raise ParseError(
                code="unsupported_source_type",
                message=f"Unsupported source type: {source_type.value}.",
                details={"source_type": source_type.value},
            )
        return parser


def default_parser_registry(*, include_images: bool = True) -> ParserRegistry:
    parsers: list[Parser] = [
        WebParser(),
        PdfParser(),
        WordParser(),
        PowerPointParser(),
    ]
    if include_images:
        parsers.append(ImageParser())
    return ParserRegistry(parsers)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/parsers/test_pdf.py tests/parsers/test_office.py tests/parsers/test_registry.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/parsers/pdf.py free_for_read/parsers/office.py free_for_read/parsers/registry.py tests/parsers
git commit -m "feat: add pdf and office parsers"
```

## Task 6: Parse Service Orchestration

**Files:**
- Create: `free_for_read/core/service.py`
- Test: `tests/core/test_service.py`

- [ ] **Step 1: Write failing service orchestration tests**

Create `tests/core/test_service.py`:

```python
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


class StubRegistry:
    def get(self, source_type: SourceType) -> StubParser:
        assert source_type == SourceType.WEB
        return StubParser()


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_service.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'free_for_read.core.service'`.

- [ ] **Step 3: Implement parse service**

Create `free_for_read/core/service.py`:

```python
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
        document = parser.parse(fetched.content, source_url=fetched.url)
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


def _validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ParseError(
            code="invalid_url",
            message="URL must be an absolute HTTP or HTTPS URL.",
            details={"url": url},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/core/service.py tests/core/test_service.py
git commit -m "feat: add parse service orchestration"
```

## Task 7: FastAPI Parse Endpoint And Error Responses

**Files:**
- Create: `free_for_read/api/schemas.py`
- Create: `free_for_read/api/routes.py`
- Modify: `free_for_read/api/app.py`
- Test: `tests/api/test_parse_route.py`
- Test: `tests/api/test_app.py`

- [ ] **Step 1: Write failing API route tests**

Create `tests/api/test_parse_route.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_parse_route.py tests/api/test_app.py -v`

Expected: FAIL because `create_app` does not accept `parse_service` and `/v1/parse` is missing.

- [ ] **Step 3: Implement API schemas, routes, and app wiring**

Create `free_for_read/api/schemas.py`:

```python
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
```

Create `free_for_read/api/routes.py`:

```python
from typing import Protocol

from fastapi import APIRouter

from free_for_read.api.schemas import ParseRequest, ParseResponse


class ParseServiceProtocol(Protocol):
    async def parse_url(self, url: str):
        raise NotImplementedError


def create_router(parse_service: ParseServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post("/parse", response_model=ParseResponse)
    async def parse(request: ParseRequest):
        return await parse_service.parse_url(str(request.url))

    return router
```

Modify `free_for_read/api/app.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from free_for_read.api.routes import create_router
from free_for_read.core.errors import ParseError
from free_for_read.core.service import ParseService


def create_app(parse_service: ParseService | None = None) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    service = parse_service or ParseService()
    app.include_router(create_router(service))

    @app.exception_handler(ParseError)
    async def parse_error_handler(request: Request, exc: ParseError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": exc.to_dict()})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_parse_route.py tests/api/test_app.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/api tests/api
git commit -m "feat: add parse api route"
```

## Task 8: End-To-End URL Parsing Tests And Final Verification

**Files:**
- Modify: `README.md`
- Test: `tests/api/test_parse_integration.py`

- [ ] **Step 1: Write failing integration tests using mocked remote URLs**

Create `tests/api/test_parse_integration.py`:

```python
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from free_for_read.api.app import create_app


def test_parse_endpoint_parses_mocked_html_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/article",
        content=b"<html><body><article><h1>Article</h1><p>Readable text.</p></article></body></html>",
        headers={"content-type": "text/html", "content-length": "85"},
    )
    client = TestClient(create_app())

    response = client.post("/v1/parse", json={"url": "https://example.com/article"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"] == "# Article\n\nReadable text."
    assert payload["document"]["root"]["children"][0]["type"] == "heading"
    assert payload["metadata"]["title"] == "Article"
    assert payload["metadata"]["source_type"] == "web"


def test_parse_endpoint_returns_unsupported_for_mocked_image_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/image.png",
        content=b"\x89PNG\r\n\x1a\n",
        headers={"content-type": "image/png", "content-length": "8"},
    )
    client = TestClient(create_app())

    response = client.post("/v1/parse", json={"url": "https://example.com/image.png"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_source_type"
```

- [ ] **Step 2: Run tests to verify they fail if earlier tasks are incomplete**

Run: `pytest tests/api/test_parse_integration.py -v`

Expected before Task 7 completion: FAIL because the parse route or service is incomplete. Expected after Task 7 completion: PASS.

- [ ] **Step 3: Update README with runnable API examples**

Modify `README.md`:

````markdown
# Free for Read

Free for Read is a backend parsing API that turns remote web pages and documents into clean Markdown, a unified document AST, and metadata for LLM and RAG workflows.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn free_for_read.api.app:create_app --factory --reload
```

## Parse A URL

```bash
curl -X POST http://127.0.0.1:8000/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article"}'
```

The response contains:

- `markdown`: clean Markdown text
- `document`: source-neutral document AST
- `metadata`: title, source URL, source type, word count, processing time, and content length

Images return `unsupported_source_type` until OCR support is added.
````

- [ ] **Step 4: Run full verification**

Run: `pytest -v`

Expected: PASS with all tests passing.

Run: `ruff check .`

Expected: PASS with no lint errors.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/api/test_parse_integration.py
git commit -m "test: add parse api integration coverage"
```

## Self-Review Notes

- Spec coverage: URL-only input is covered by Tasks 3, 6, 7, and 8. Web, PDF, Word, PowerPoint, and image unsupported behavior are covered by Tasks 4 and 5. Markdown, AST, and metadata are covered by Tasks 2, 6, 7, and 8. Structured errors are covered by Tasks 3 and 7.
- Scope: reader UI, local uploads, model configuration, AI question answering, persistence, RAG indexing, OCR, background jobs, and deployment remain out of scope.
- Type consistency: source types use the `SourceType` enum values `web`, `pdf`, `word`, `powerpoint`, and `image`. The route returns `ParseResponse` with `markdown`, `document`, and `metadata`.
- Verification: completion requires fresh `pytest -v` and `ruff check .` runs after Task 8.
