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

The response contains:

- `markdown`: clean Markdown text
- `document`: source-neutral document AST
- `metadata`: title, source URL, source type, word count, processing time, and content length

Images return `unsupported_source_type` until OCR support is added.

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
