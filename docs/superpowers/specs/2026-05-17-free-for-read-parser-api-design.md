# Free for Read Parser API Design

Date: 2026-05-17

## Goal

Free for Read starts as a backend parsing API for remote content. A client sends a URL, and the service fetches the source, detects its type, parses it into a unified document tree, renders clean Markdown, and returns metadata that is suitable for LLM and RAG pipelines.

This first phase focuses on the parser API only. Reading UI, local file uploads, model configuration, AI question answering, persistent libraries, and RAG indexing are intentionally out of scope for this spec.

## MVP Scope

The API accepts URL input only.

Supported first-pass source types:

- Web pages
- PDF documents
- Word documents
- PowerPoint documents

Images are represented as an explicit extension point. The first version detects image URLs and returns a structured `unsupported_source_type` error until OCR support is added.

The response contains:

- A clean Markdown string
- A complete document AST
- Metadata including title, source URL, source type, word count, processing time, and content length when available

## Recommended Approach

Use a modular parsing kernel with a unified AST.

FastAPI remains thin and stateless. It validates requests, delegates work to the parsing service, and serializes responses. The parsing service owns fetching, type detection, parser selection, Markdown rendering, and metadata building.

This gives the project an open-source-friendly shape: each parser is isolated, the core data model is stable, and future features such as uploads, OCR, async jobs, caching, chunking, RAG indexing, and reader progress can be added without replacing the first API.

## Architecture

```text
Client
  -> FastAPI REST API
    -> Parse Service
      -> URL Fetcher
      -> Content Type Detector
      -> Parser Registry
        -> WebParser
        -> PdfParser
        -> WordParser
        -> PowerPointParser
        -> ImageParser unsupported stub
      -> Markdown Renderer
      -> Metadata Builder
    -> JSON Response
```

## Package Layout

```text
free_for_read/
  api/
    app.py
    routes.py
    schemas.py
  core/
    models.py
    service.py
    errors.py
  fetchers/
    url_fetcher.py
  detectors/
    content_type.py
  parsers/
    base.py
    registry.py
    web.py
    pdf.py
    office.py
    image.py
  renderers/
    markdown.py
  metadata/
    builder.py
tests/
```

## Core Models

The central model is a source-neutral document tree.

`Document` represents one parsed source. It contains the root node and source-level metadata that parsers can discover, such as title.

`DocumentNode` represents a block or structural unit. Initial node types:

- `document`
- `heading`
- `paragraph`
- `list`
- `list_item`
- `table`
- `table_row`
- `table_cell`
- `image`
- `page_break`
- `slide`

Each node can hold:

- `type`
- `text`
- `level`
- `children`
- `metadata`

Node metadata is intentionally flexible so parsers can preserve page numbers, slide numbers, source anchors, or layout hints without changing the schema every time.

## API Contract

Endpoint:

```http
POST /v1/parse
```

Request:

```json
{
  "url": "https://example.com/book.pdf"
}
```

Success response:

```json
{
  "markdown": "# Title\n\nClean text...",
  "document": {
    "type": "document",
    "children": []
  },
  "metadata": {
    "title": "Title",
    "source_url": "https://example.com/book.pdf",
    "source_type": "pdf",
    "word_count": 1234,
    "processing_ms": 388,
    "content_length": 456789
  }
}
```

Structured error response:

```json
{
  "error": {
    "code": "fetch_timeout",
    "message": "Timed out while fetching source URL.",
    "details": {
      "url": "https://example.com/book.pdf"
    }
  }
}
```

## Data Flow

1. Validate the request URL.
2. Fetch the URL with a timeout, size limit, redirect handling, and a clear User-Agent.
3. Detect source type from response headers, URL extension, and lightweight content sniffing.
4. Select a parser through the parser registry.
5. Parse the raw content into a unified `Document` AST.
6. Render the AST to Markdown.
7. Build response metadata.
8. Return the response JSON.

## Parser Responsibilities

`WebParser` extracts the main article or page body, removes navigation and advertising noise, maps headings and paragraphs into the AST, and preserves the best available title.

`PdfParser` extracts text page by page, preserving page boundaries through `page_break` metadata and creating paragraphs where possible.

`WordParser` maps Word headings and paragraphs into heading and paragraph nodes. Lists and tables are represented when the underlying library exposes them cleanly.

`PowerPointParser` maps each slide to a `slide` node, preserving slide number and extracting title/body text where possible.

`ImageParser` exists as an unsupported parser stub. It reports unsupported input until OCR is deliberately introduced.

## Dependencies

Runtime dependencies:

- `fastapi`
- `uvicorn`
- `pydantic-settings`
- `httpx`
- `trafilatura`
- `beautifulsoup4`
- `pypdf`
- `python-docx`
- `python-pptx`

Development dependencies:

- `pytest`
- `pytest-httpx` or `respx`
- `ruff`

The dependency strategy favors small, well-known libraries for the first version. Heavy OCR or layout intelligence packages are deferred.

## Error Handling

Errors are domain errors inside the core service and are converted to API error responses at the boundary.

Initial error codes:

- `invalid_url`
- `fetch_timeout`
- `fetch_failed`
- `content_too_large`
- `unsupported_source_type`
- `parse_failed`

All error responses include a stable machine-readable code, a human-readable message, and optional details.

## Testing Strategy

Unit tests:

- Content type detection
- Markdown rendering
- Metadata building
- Parser registry behavior

Parser tests:

- Small HTML fixture
- Small PDF fixture
- Small DOCX fixture
- Small PPTX fixture
- Image unsupported path

API tests:

- `/v1/parse` success path using mocked URL responses
- Fetch timeout or fetch failure
- Unsupported source type
- Parse failure mapping

The first implementation follows test-driven development: write a failing behavior test, verify the failure, implement the minimal code, then verify the test passes.

## Out of Scope For This Spec

- Local file upload
- User accounts
- Persistent document storage
- Frontend reader
- Model/API key configuration
- AI question answering
- Vector indexing and retrieval
- OCR
- Background job queues
- Distributed deployment

## Future Extension Points

- Add `/v1/parse/file` for local uploads.
- Add async parsing jobs for large documents.
- Add OCR-backed image parsing.
- Add chunk generation for RAG.
- Add persistent document libraries.
- Add reader progress and annotation APIs.
- Add AI question answering over parsed documents.
