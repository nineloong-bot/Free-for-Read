# Free for Read

Free for Read is a backend parsing API that turns remote web pages and documents into clean
Markdown, a unified document AST, and metadata for LLM and RAG workflows.

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

## Parse A Local File

```bash
curl -X POST http://127.0.0.1:8000/v1/parse/file \
  -F "file=@./document.pdf"
```

Or by local file path:

```bash
curl -X POST http://127.0.0.1:8000/v1/parse/file \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/document.docx"}'
```

## CLI Server

```bash
free-for-read serve --port 0
```

Starts the API on an ephemeral port and prints `READY http://127.0.0.1:{port}` for sidecar orchestration.

## Import An Ebook

The response contains:

- `markdown`: clean Markdown text
- `document`: source-neutral document AST
- `metadata`: title, source URL, source type, word count, processing time, and content length

Images return `unsupported_source_type` until OCR support is added.

## Import An Ebook

```bash
curl -X POST http://127.0.0.1:8000/v1/books/import \
  -F "file=@./book.epub"
```

Supported ebook formats are EPUB, FB2, and FBZ. Imported source files and the
SQLite library database are stored under `storage/` by default.

## Library Endpoints

- `POST /v1/books/import`: import an ebook file.
- `GET /v1/books`: list imported books.
- `GET /v1/books/{book_id}`: get book details with chapter summaries.
- `GET /v1/books/{book_id}/chapters`: list chapters for a book.
- `GET /v1/books/{book_id}/chapters/{chapter_id}`: get chapter Markdown.
- `GET /v1/books/{book_id}/progress`: get saved reading progress.
- `PUT /v1/books/{book_id}/progress`: save reading progress.
- `POST /v1/books/{book_id}/bookmarks`: create a bookmark.
- `GET /v1/books/{book_id}/bookmarks`: list bookmarks.
- `DELETE /v1/books/{book_id}/bookmarks/{bookmark_id}`: delete a bookmark.
- `POST /v1/books/{book_id}/reindex`: reindex book into AI vector store.
- `GET /v1/books/{book_id}/index`: check book indexing status.

## AI Reading (Phase 5)

Configure AI via environment variables:

- `AI_PROVIDER`: `openai` | `anthropic` | `ollama` (default: `openai`)
- `AI_API_KEY`: Provider API key
- `AI_BASE_URL`: Custom endpoint (for OpenAI-compatible APIs or Ollama)
- `EMBED_PROVIDER`: `local` | `openai` (default: `local`)
- `CHROMA_PATH`: ChromaDB storage path (default: `storage/chroma`)

### Chat with a Book

```bash
curl -X POST http://127.0.0.1:8000/v1/books/{book_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"这一章的核心主题是什么？"}'
```

### Semantic Search

```bash
curl "http://127.0.0.1:8000/v1/books/search?q=红岸基地&limit=10"
```

### Reindex a Book

```bash
curl -X POST http://127.0.0.1:8000/v1/books/{book_id}/reindex
```

## Errors

Invalid URLs, unsupported source types, fetch failures, oversized content, and parse
failures return a structured error payload:

```json
{
  "error": {
    "code": "unsupported_source_type",
    "message": "Unsupported source type: image.",
    "details": {
      "source_type": "image"
    }
  }
}
```

Request validation errors use the same envelope with `code` set to `invalid_url`.
