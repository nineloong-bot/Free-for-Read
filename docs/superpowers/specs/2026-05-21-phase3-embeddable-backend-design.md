# Phase 3: Embeddable Backend & Local File Support Design

Date: 2026-05-21

## Goal

Make the Python backend runnable as a standalone binary that Tauri can spawn as a sidecar. Add local file parsing and lifecycle management so the desktop app can parse both remote URLs and local documents through the same API.

## Scope

This phase includes:

- CLI entry point with ephemeral port selection.
- PyInstaller packaging producing single binaries for macOS, Windows, and Linux.
- `POST /v1/parse/file` accepting multipart uploads and local file paths.
- `POST /shutdown` endpoint for clean sidecar exit from Tauri.
- Tests for CLI, local file parsing, and shutdown behavior.

This phase does not include:

- Tauri project scaffolding (Phase 4).
- Frontend or reading UI (Phase 4).
- CI/CD build pipelines (Phase 6).
- Code signing or notarization (Phase 6).
- AI features (Phase 5).

## Architecture

The backend stays a standard FastAPI process with no knowledge of Tauri.

```
Tauri (Phase 4)
  │
  ├── spawn: free-for-read serve --port 0
  │     → reads "READY http://127.0.0.1:PORT" from stdout
  │     → proxies requests to localhost:PORT
  │
  └── shutdown: POST http://127.0.0.1:PORT/shutdown
        → backend exits cleanly
```

## CLI Entry Point

### `free_for_read/cli.py`

A `serve` subcommand:

```
free-for-read serve [--host 127.0.0.1] [--port 0] [--storage ./storage]
```

Behavior:

1. Resolve host and port. When port is 0, bind to an OS-assigned ephemeral port.
2. Build the FastAPI app via `create_app()` with the configured storage root.
3. Start uvicorn programmatically with `log_config=None` to suppress its default banner.
4. After the server is listening, print `READY http://{host}:{port}` to stdout (exact format so Tauri can parse it).
5. Register signal handlers for `SIGTERM` and `SIGINT` that trigger graceful shutdown.

`--port 0` is the production default for Tauri. `--port 8000` is available for development.

### Dependencies

- `click>=8.0` for CLI argument parsing.

## PyInstaller Packaging

### Configuration

`pyproject.toml` gains a `[tool.pyinstaller]` section or a standalone `free-for-read.spec` file.

Requirements:

- Single-file output (`--onefile`).
- Entry point: `free_for_read/cli.py` (the `serve` command).
- Hidden imports: `uvicorn.protocols.http.auto`, `uvicorn.loops.auto`.
- macOS: `--target-architecture universal2` (or separate arm64/x86_64 builds).
- Windows: `--noconsole` for release, console kept for debug builds.
- Collect submodules: `free_for_read/**/*.py`, `defusedxml`, `bs4`, `trafilatura`.

### Build commands

```makefile
# Makefile targets
build-macos:   PyInstaller --onefile free_for_read/cli.py --name free-for-read ...
build-windows: Same on Windows runner
build-linux:   Same on Linux runner
```

CI matrices and auto-release are deferred to Phase 6. Phase 3 only requires a local `make build` that produces a runnable binary on the current platform.

## `/v1/parse/file` Endpoint

### Request

Two input modes, discriminated by the request shape:

**Multipart mode** (parity with `/v1/books/import`):

```http
POST /v1/parse/file
Content-Type: multipart/form-data

file: @document.pdf
```

**Path mode** (Tauri drag-and-drop, local file on disk):

```json
{
  "path": "/Users/alice/Documents/report.docx"
}
```

### Behavior

1. Read the content. For multipart, read the uploaded bytes. For path mode, read the file from disk.
2. Reject unsafe paths (traversal, absolute paths outside allowed roots) in path mode.
3. Detect source type from filename and content (reuses `detect_source_type` from `free_for_read/detectors/content_type.py`).
4. Select parser from the existing registry.
5. Parse, render, and build metadata (same pipeline as `POST /v1/parse`).
6. Return identical response shape.

### Response

Same as `POST /v1/parse`:

```json
{
  "markdown": "# Title\n\nClean text...",
  "document": { ... },
  "metadata": { ... }
}
```

### Error handling

Reuses the existing `ParseError` envelope. New error code:

- `invalid_file_path` — path contains traversal or points outside allowed directories.

## `/shutdown` Endpoint

### Request

```http
POST /shutdown
```

### Behavior

1. Return `{"status": "shutting_down"}`.
2. Start a background task that calls `sys.exit(0)` after a short delay (allows the response to flush).

Tauri calls this before quitting to ensure the sidecar exits cleanly rather than being forcefully killed.

### Security

`/shutdown` is only bound to `127.0.0.1` (localhost). It is not exposed on external interfaces. If a remote binding is configured, `/shutdown` must be disabled or require an authentication token (out of scope for now, since Tauri sidecar always uses localhost).

## Files to Create or Modify

- Create: `free_for_read/cli.py` — CLI entry point with `serve` command.
- Create: `free_for_read/api/parse_file_routes.py` — `/v1/parse/file` route.
- Create: `free_for_read/api/parse_file_schemas.py` — request schemas for the new route.
- Modify: `free_for_read/api/app.py` — wire parse-file router and `/shutdown` endpoint.
- Modify: `pyproject.toml` — add `click` dependency and PyInstaller config.
- Create: `Makefile` — build targets for packaging.
- Create: `tests/api/test_parse_file_routes.py` — tests for local file parsing and shutdown.

## Testing

### CLI tests

- `serve --port 0` starts and prints READY line with an assigned port.
- `serve --port 8000` starts on the specified port.
- Server responds to `/health` after READY.
- `SIGTERM` triggers graceful shutdown.

### Parse file route tests

- Multipart upload of a PDF returns the same response shape as `/v1/parse`.
- Multipart upload of a DOCX returns heading and paragraphs.
- Path mode with a valid file path parses correctly.
- Path mode rejects traversal (`../../../etc/passwd`).
- Path mode rejects non-existent files.
- Unsupported extension returns `unsupported_source_type`.

### Shutdown test

- `POST /shutdown` returns `{"status": "shutting_down"}` with status 200.

## Dependencies

- `click>=8.0` — CLI argument parsing.
- `pyinstaller>=6.0` — binary packaging (dev dependency, not bundled at runtime).

## Acceptance Criteria

- `free-for-read serve --port 0` starts and prints a parseable READY line.
- `POST /v1/parse/file` with a multipart PDF/DOCX returns a valid parse response.
- `POST /v1/parse/file` with a local path works for files within the storage root.
- `POST /v1/parse/file` rejects path traversal and non-existent files.
- `POST /shutdown` returns 200 and initiates graceful exit.
- `make build` produces a working single-file binary.
- Existing `/v1/parse` and `/v1/books/*` routes are unchanged.
- Full test suite and linter pass.

## Out of Scope

- Tauri project scaffolding (Phase 4).
- Cross-platform CI builds (Phase 6).
- Code signing, notarization, installer packaging (Phase 6).
- AI features (Phase 5).
- OCR, async jobs, user accounts.
