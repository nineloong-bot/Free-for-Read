# Ebook Library Design

## Purpose

Free for Read will grow from a stateless parsing API into the backend foundation for
an AI reading application. This phase adds ebook ingestion and a small persisted
library while keeping the parser engine reusable.

The goal is to support importing EPUB, FB2, and FBZ novels, extracting clean
chapter-level Markdown, and exposing book, chapter, reading progress, and bookmark
APIs. The MVP stores files locally and metadata in SQLite, but it must keep storage
and repository boundaries explicit so later deployments can move to object storage
and PostgreSQL without rewriting the API layer.

## Scope

This phase includes:

- EPUB parsing into ordered chapters.
- FB2 parsing into ordered chapters.
- FBZ parsing by extracting the contained FB2 file.
- File upload import API.
- Local file storage implementation behind a storage interface.
- SQLite repository implementation behind a repository interface.
- Book list, book detail, chapter list, chapter detail, progress, and bookmark APIs.
- Tests for parsers, storage, repository, and API behavior.

This phase does not include:

- MOBI, AZW, AZW3, or CBZ.
- DRM removal or DRM bypass.
- OCR.
- AI chat, embeddings, vector search, or RAG.
- User accounts.
- Notes and highlights.
- Frontend reading UI.

## Architecture

The existing `/v1/parse` endpoint remains unchanged. Ebook library behavior is added
as a separate module so the parser API stays useful for one-shot conversions.

New modules:

- `free_for_read/parsers/ebooks.py`
  EPUB, FB2, and FBZ parsing logic.
- `free_for_read/library/models.py`
  Pydantic/domain models for books, chapters, progress, and bookmarks.
- `free_for_read/library/storage.py`
  Storage interface plus local filesystem implementation.
- `free_for_read/library/repository.py`
  Repository interface plus SQLite implementation.
- `free_for_read/library/service.py`
  Import, lookup, progress, and bookmark orchestration.
- `free_for_read/api/library_routes.py`
  REST API routes for library operations.
- `free_for_read/api/library_schemas.py`
  Request and response schemas.

The service layer depends on storage and repository interfaces rather than concrete
SQLite or local filesystem classes. App construction wires the MVP implementations.

## Data Model

### Book

- `id`: stable generated identifier.
- `title`: display title.
- `author`: optional author string.
- `language`: optional language code.
- `source_type`: `epub`, `fb2`, or `fbz`.
- `original_filename`: uploaded filename.
- `storage_path`: stored source file path or storage key.
- `cover_path`: optional stored cover path or storage key.
- `word_count`: total parsed word count.
- `chapter_count`: number of parsed chapters.
- `created_at`: import timestamp.
- `updated_at`: last update timestamp.

### Chapter

- `id`: stable generated identifier.
- `book_id`: owning book id.
- `index`: zero-based chapter order.
- `title`: chapter title.
- `markdown`: clean chapter Markdown.
- `word_count`: chapter word count.
- `source_ref`: EPUB href, FB2 section path, or similar source reference.
- `metadata`: format-specific structured metadata.

### ReadingProgress

- `book_id`: owning book id.
- `chapter_id`: current chapter id.
- `position`: JSON object stored as text in SQLite.
- `updated_at`: last progress update timestamp.

The `position` object is intentionally UI-neutral. A reader can store values such
as `{"paragraph": 18, "offset": 120}` without forcing the backend to know the
frontend layout.

### Bookmark

- `id`: stable generated identifier.
- `book_id`: owning book id.
- `chapter_id`: target chapter id.
- `position`: JSON object stored as text in SQLite.
- `label`: optional user-visible label.
- `created_at`: creation timestamp.

## Parsing Strategy

### EPUB

EPUB parsing uses the package structure instead of treating the file as a flat ZIP.

Flow:

1. Open the EPUB as ZIP.
2. Read `META-INF/container.xml`.
3. Resolve the OPF package path.
4. Parse OPF metadata, manifest, and spine.
5. Resolve `nav.xhtml` or NCX table-of-contents data when present.
6. Read spine items in order.
7. Parse each XHTML/HTML item into clean Markdown.
8. Create one chapter per spine item with a title from TOC, first heading, or
   fallback `Chapter N`.

The parser should reject path traversal entries and malformed package references.
XML files inside the package should be parsed with an XML parser that disables
external entity expansion. Images are not embedded in Markdown in this phase.
`cover_path` remains `null` unless a cover file can be identified directly from
standard OPF metadata without heuristic image detection.

### FB2

FB2 parsing treats the file as XML.

Flow:

1. Parse XML with external entity expansion disabled.
2. Read `description/title-info` for title, author, and language.
3. Traverse `body/section` elements in document order.
4. Map each top-level section to a chapter.
5. Use `section/title` as the chapter title when present.
6. Convert paragraphs and simple text blocks into Markdown.

Poems, citations, epigraphs, and subtitles can be flattened into paragraph-style
Markdown for the MVP. Binary images are recorded only as metadata or ignored.

### FBZ

FBZ parsing opens the archive, finds the first `.fb2` file, rejects unsafe paths,
and then delegates to the FB2 parser.

## API Design

### Import Book

`POST /v1/books/import`

Request:

- `multipart/form-data`
- field: `file`

Supported extensions:

- `.epub`
- `.fb2`
- `.fbz`

Behavior:

1. Validate extension and content.
2. Save original file through `StorageBackend`.
3. Parse chapters.
4. Persist book and chapters in one repository transaction.
5. Return book detail plus chapter summaries.

### List Books

`GET /v1/books?limit=50&offset=0`

Returns books ordered by `created_at desc`. The response includes enough metadata
for a library view but not chapter Markdown.

### Get Book

`GET /v1/books/{book_id}`

Returns book metadata, chapter count, word count, and progress summary when present.

### List Chapters

`GET /v1/books/{book_id}/chapters`

Returns ordered chapter summaries without full Markdown.

### Get Chapter

`GET /v1/books/{book_id}/chapters/{chapter_id}`

Returns chapter title, Markdown, word count, and previous/next chapter ids.

### Get Progress

`GET /v1/books/{book_id}/progress`

Returns current progress or `null` when no progress exists.

### Update Progress

`PUT /v1/books/{book_id}/progress`

Request body:

- `chapter_id`
- `position`

The service verifies that the chapter belongs to the book before saving.

### Create Bookmark

`POST /v1/books/{book_id}/bookmarks`

Request body:

- `chapter_id`
- `position`
- `label` optional

### List Bookmarks

`GET /v1/books/{book_id}/bookmarks`

Returns bookmarks ordered by `created_at asc`.

### Delete Bookmark

`DELETE /v1/books/{book_id}/bookmarks/{bookmark_id}`

Deletes a bookmark after verifying it belongs to the book.

## Error Handling

Library APIs use the existing structured error envelope:

```json
{
  "error": {
    "code": "unsupported_ebook_format",
    "message": "Unsupported ebook format.",
    "details": {}
  }
}
```

New error codes:

- `unsupported_ebook_format`
- `invalid_ebook`
- `book_not_found`
- `chapter_not_found`
- `bookmark_not_found`
- `storage_failed`
- `repository_failed`

The first implementation can reuse the current HTTP status behavior, but the route
layer should keep error code mapping centralized so status-specific behavior can be
added later.

## Storage

`StorageBackend` responsibilities:

- Save an uploaded source file.
- Return a stable storage key or path.
- Reject unsafe filenames and traversal attempts.
- Avoid accidental overwrites by generating unique names.

`LocalStorageBackend` stores files under a configurable `storage/` directory. The
directory is outside Python packages and should be ignored by git.

## Repository

`LibraryRepository` responsibilities:

- Initialize schema.
- Insert a book and its chapters transactionally.
- List books.
- Fetch book, chapters, and chapter details.
- Upsert reading progress.
- Create, list, and delete bookmarks.

`SQLiteLibraryRepository` uses the standard `sqlite3` module for the MVP. It stores
JSON fields as text and converts them at the repository boundary.

## Testing

Parser tests:

- Minimal EPUB with OPF, manifest, spine, and two XHTML chapters.
- EPUB title fallback from first heading when TOC title is absent.
- Minimal FB2 with metadata and two sections.
- FBZ archive containing one FB2 file.
- Invalid archive and malformed XML errors.

Storage tests:

- Saves uploaded files.
- Generates unique names for repeated filenames.
- Rejects unsafe filenames or paths.

Repository tests:

- Inserts book and chapters transactionally.
- Lists and fetches books.
- Fetches ordered chapters.
- Upserts reading progress.
- Creates, lists, and deletes bookmarks.

API tests:

- Upload EPUB and receive book plus chapter summaries.
- Upload FB2 and receive book plus chapter summaries.
- Reject unsupported extension.
- List books.
- Fetch chapter Markdown.
- Update and fetch progress.
- Create, list, and delete bookmarks.

## Acceptance Criteria

- Existing `/v1/parse` behavior is unchanged.
- `POST /v1/books/import` can import valid EPUB, FB2, and FBZ fixtures.
- Imported books are persisted in SQLite and visible through `GET /v1/books`.
- Chapters are returned in source reading order.
- Chapter Markdown is clean enough to read directly and suitable for later RAG.
- Progress and bookmarks can be saved and retrieved.
- Storage and repository implementations are replaceable through interfaces.
- Full test suite and linter pass.
