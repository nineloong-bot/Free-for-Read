# Route B Roadmap: From Backend API to Tauri Desktop Reading App

## Context

Route:
- Package FastAPI as a Tauri sidecar process (PyInstaller binary)
- Use React + foliate-js for the reading UI
- Desktop access to local filesystem via Tauri's Rust layer (drag-and-drop import, file associations)
- Incrementally migrate parsing logic to Rust over time for performance and smaller bundle size

Phase 1 (stateless parse API) is done. Phase 2 (ebook library with EPUB/FB2/FBZ, SQLite persistence, progress, bookmarks) is done. The long-term goal is a Tauri desktop reading app that embeds the Python backend as a sidecar process.

The original Phase 1 spec listed "Future Extension Points" designed for a cloud API service: file upload, OCR, async jobs, RAG chunking, AI Q&A, vector indexing. For this new route, several are misaligned — a local desktop app doesn't need background job queues, user accounts, or distributed deployment. The roadmap is reshaped around the needs of a local-first reading experience.

## Key Decision: Reshape After Phase 2

The original extension points should NOT be followed in order. Instead, after Phase 2, pivot to **client-readiness**:

| Decision | Items | Why |
|----------|-------|-----|
| **Keep** | `/v1/parse/file`, RAG chunking, AI Q&A | Core to a reading app with AI features |
| **Defer** | OCR | High complexity, low MVP impact |
| **Skip** | Async job queues, user accounts, distributed deployment | Local desktop app doesn't need these |

## Architecture

```
Tauri Desktop App (Rust process)
│
├── Main Window (React + TypeScript webview)
│   ├── Library View — browse imported books
│   ├── Reader View — foliate-js rendering + progress sync
│   ├── Parser View — URL / local file → Markdown preview
│   └── AI Panel — chat about current book, semantic search
│
├── Sidecar: Python Backend (FastAPI on localhost:PORT)
│   ├── /v1/parse          — URL → Markdown (Phase 1)
│   ├── /v1/parse/file     — local file → Markdown (Phase 3)
│   ├── /v1/books/*         — ebook library + progress + bookmarks (Phase 2)
│   ├── /v1/books/*/chunks  — RAG chunking (Phase 5)
│   └── /v1/books/*/chat    — AI Q&A (Phase 5)
│
└── Sidecar: Ollama (optional, for offline AI)
```

The Python backend has no knowledge of Tauri — it binds to `127.0.0.1` on an ephemeral port. Tauri's Rust layer spawns the sidecar, finds the port, routes frontend requests, and manages lifecycle.

## Phase Breakdown

### Phase 2: Ebook Library

EPUB, FB2, FBZ import with chapter extraction, SQLite persistence, reading progress, and bookmarks API.

### Phase 3: Embeddable Backend & Local File Support

**Goal**: Make the backend runnable as a standalone sidecar. Add local file parsing.

1. **PyInstaller packaging** — single binary per platform. Starts uvicorn on ephemeral port, prints port to stdout for Tauri.

2. **`POST /v1/parse/file`** — accepts multipart upload or local file path. Reuses the existing detector → parser → renderer pipeline unchanged.

3. **Lifecycle** — `GET /health` already exists. Add `POST /shutdown` for clean exit.

**Files to create/modify:**
- `free_for_read/api/routes.py` — add local file route
- `free_for_read/cli.py` — CLI entry with port selection
- `pyproject.toml` — PyInstaller config

### Phase 4: Tauri Shell & Reading UI

**Goal**: Working desktop app with library, EPUB reading, and document parsing.

1. **Tauri project** — sidecar management (spawn Python binary, read port, health-check, kill on exit).

2. **React frontend** — three views:
   - **Library View**: grid/list, upload, delete, progress indicator
   - **Reader View**: foliate-js EPUB rendering, auto-save progress, bookmark toggle, chapter nav
   - **Parser View**: URL input or file drop → rendered Markdown

3. **Platform integration** — system tray, file associations, native file dialog, drag-and-drop.

4. **API client** — typed TypeScript client matching the `ParseError` error envelope.

**Files to create:**
- `tauri/` — full Tauri project
- `frontend/` — React app

### Phase 5: AI Reading Features

**Goal**: Chat about books, semantic search, RAG-powered Q&A.

1. **Chunking** — heading-aware chapter splitting. `free_for_read/ai/chunking.py`.

2. **Embeddings** — local (sentence-transformers or Transformers.js) or API-based. Stored alongside SQLite.

3. **`POST /v1/books/{id}/chat`** — user question + context → answer + source citations. Delegates to configured LLM.

4. **`GET /v1/books/{id}/search`** — hybrid search (BM25 + vector similarity) → ranked excerpts.

5. **Frontend AI Panel** — chat sidebar in reader, search bar in library.

**Files to create:**
- `free_for_read/ai/`
- `free_for_read/api/ai_routes.py`

### Phase 6: Polish & Distribution

**Goal**: Ship-ready desktop app.

1. **CI builds** — GitHub Actions for `.dmg`, `.msi`, `.AppImage`.
2. **Auto-update** — Tauri updater → GitHub Releases.
3. **Offline mode** — all features without network (Ollama for AI, local parsers).
4. **Settings** — AI provider config, reading preferences.

## Timeline

| Phase | Content |
|---|---|
| Phase 2 | Ebook library |
| Phase 3 | Packaging + local files |
| Phase 4 | Tauri shell + reading UI |
| Phase 5 | AI reading features |
| Phase 6 | Polish & distribution |

Phase 4 is the critical path — the moment the project becomes an application rather than an API. Everything before it prepares; everything after differentiates.

## Verification Per Phase

**Phase 3**: PyInstaller binary starts and responds to `/health`; `POST /v1/parse/file` returns same shape as `POST /v1/parse`.

**Phase 4**: Tauri app launches, imports an EPUB, renders it in foliate-js, saves progress across restarts.

**Phase 5**: "What is the main theme of this chapter?" returns grounded answer with source citations.

**Phase 6**: Fresh install opens `.epub` files, works offline, updates itself via Tauri updater.
