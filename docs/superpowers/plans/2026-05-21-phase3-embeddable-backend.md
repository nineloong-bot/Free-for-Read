# Phase 3: Embeddable Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Python backend runnable as a standalone binary for Tauri sidecar management, add local file parsing, and lifecycle endpoints.

**Architecture:** Add `parse_content` to ParseService to reuse the existing detector→parser→renderer pipeline for local files. Wire a new `/v1/parse/file` route that handles both multipart uploads and local path references. Introduce a CLI entry point (`free-for-read serve`) that binds an ephemeral port and prints a machine-parseable READY line. Add `/shutdown` for clean sidecar exit. Package everything as a single-file PyInstaller binary.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Click, PyInstaller, pytest.

---

## File Structure

- Modify: `free_for_read/core/service.py`
  Add `parse_content()` method that accepts raw bytes and reuses the detector→parser→renderer pipeline.
- Create: `free_for_read/api/parse_file_schemas.py`
  Pydantic schemas for the local-file parse request.
- Create: `free_for_read/api/parse_file_routes.py`
  `/v1/parse/file` route handling multipart and path modes.
- Modify: `free_for_read/api/app.py`
  Wire parse-file router, add `/shutdown` endpoint, accept `storage_root` parameter.
- Create: `free_for_read/cli.py`
  CLI entry point with `serve` command, ephemeral port binding, signal handling, and READY line output.
- Modify: `pyproject.toml`
  Add `click` dependency, `free-for-read` script entry point, optional PyInstaller dependency.
- Create: `Makefile`
  Build targets for platform binaries.
- Create: `tests/api/test_parse_file_routes.py`
  Tests for parse-file route (multipart, path mode, path rejection, unsupported type).
- Create: `tests/cli/__init__.py`
- Create: `tests/cli/test_cli.py`
  Tests for CLI serve command, port binding, and READY line.
- Create: `tests/api/test_shutdown.py`
  Test for `/shutdown` endpoint behavior.

---

### Task 1: Core Service Parse-Content Method

**Files:**
- Modify: `free_for_read/core/service.py`
  Add `parse_content()` to `ParseService`.
- Test: `tests/core/test_service.py`

- [ ] **Step 1: Write failing test for parse_content**

Add to `tests/core/test_service.py`:

```python
from dataclasses import dataclass

from free_for_read.core.models import Document, DocumentNode, SourceType


@dataclass(frozen=True)
class StubParsedContent:
    url: str
    content: bytes
    content_type: str | None
    content_length: int | None


class StubParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        return Document(
            root=DocumentNode(
                type="document",
                children=[
                    DocumentNode(type="heading", text="Local", level=1),
                    DocumentNode(type="paragraph", text="File content."),
                ],
            ),
            title="Local",
        )


class StubRegistry:
    def get(self, source_type: SourceType) -> StubParser:
        return StubParser()


def test_parse_content_reuses_pipeline_for_local_bytes() -> None:
    service = ParseService(fetcher=StubFetcher(), registry=StubRegistry())

    result = service.parse_content(
        content=b"<html>local</html>",
        filename="local.html",
        source_url="file://local.html",
    )

    assert result.markdown == "# Local\n\nFile content."
    assert result.document.title == "Local"
    assert result.metadata.source_type == SourceType.WEB
    assert result.metadata.content_length == 31
    assert result.metadata.processing_ms >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/core/test_service.py::test_parse_content_reuses_pipeline_for_local_bytes -v
```

Expected: FAIL because `ParseService` has no `parse_content` method.

- [ ] **Step 3: Implement parse_content on ParseService**

Modify `free_for_read/core/service.py` — add `parse_content` method inside `ParseService` after `parse_url`:

```python
def parse_content(self, content: bytes, *, filename: str, source_url: str) -> ParseResult:
    source_type = detect_source_type(
        url=source_url,
        content_type=None,
        content=content,
    )
    parser = self.registry.get(source_type)
    document = parser.parse(content, source_url=source_url)
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
```

The method is synchronous (no network I/O) and reuses the same detector, parser registry, renderer, and metadata builder as `parse_url`.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run --extra dev pytest tests/core/test_service.py -v
```

Expected: All 5 tests PASS (4 existing + 1 new).

- [ ] **Step 5: Run linter**

Run:
```bash
uv run --extra dev ruff check free_for_read/core/service.py tests/core/test_service.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add free_for_read/core/service.py tests/core/test_service.py
git commit -m "feat: add local content parsing method"
```

---

### Task 2: Parse File Route

**Files:**
- Create: `free_for_read/api/parse_file_schemas.py`
- Create: `free_for_read/api/parse_file_routes.py`
- Test: `tests/api/test_parse_file_routes.py`

- [ ] **Step 1: Write failing parse-file route tests**

Create `tests/api/test_parse_file_routes.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode, ParseMetadata, SourceType
from free_for_read.core.service import ParseResult


class StubParseFileService:
    async def parse_url(self, url: str) -> ParseResult:
        raise NotImplementedError

    def parse_content(self, content: bytes, *, filename: str, source_url: str) -> ParseResult:
        return ParseResult(
            markdown="# Test\n\nContent.",
            document=Document(
                root=DocumentNode(
                    type="document",
                    children=[DocumentNode(type="heading", text="Test", level=1)],
                ),
                title="Test",
            ),
            metadata=ParseMetadata(
                title="Test",
                source_url=source_url,
                source_type=SourceType.WEB,
                word_count=2,
                processing_ms=5,
                content_length=len(content),
            ),
        )


class StubParseFileErrorService:
    async def parse_url(self, url: str) -> ParseResult:
        raise NotImplementedError

    def parse_content(self, content: bytes, *, filename: str, source_url: str) -> ParseResult:
        raise ParseError(
            code="unsupported_source_type",
            message="Unsupported source type: image.",
            details={"source_type": "image"},
        )


def test_parse_file_multipart_returns_parse_response() -> None:
    client = TestClient(create_app(parse_service=StubParseFileService()))

    response = client.post(
        "/v1/parse/file",
        files={"file": ("doc.html", b"<html>test</html>", "text/html")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"] == "# Test\n\nContent."
    assert payload["metadata"]["source_type"] == "web"


def test_parse_file_path_mode_parses_local_file(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.html"
    file_path.write_text("<html>test</html>")

    client = TestClient(create_app(parse_service=StubParseFileService()))

    response = client.post("/v1/parse/file", json={"path": str(file_path)})

    assert response.status_code == 200
    assert response.json()["markdown"] == "# Test\n\nContent."


def test_parse_file_rejects_path_traversal() -> None:
    client = TestClient(create_app(parse_service=StubParseFileService()))

    response = client.post(
        "/v1/parse/file",
        json={"path": "../../../etc/passwd"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_file_path"


def test_parse_file_rejects_nonexistent_file(tmp_path: Path) -> None:
    file_path = tmp_path / "missing.html"

    client = TestClient(create_app(parse_service=StubParseFileService()))

    response = client.post("/v1/parse/file", json={"path": str(file_path)})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_file_path"


def test_parse_file_maps_parse_errors() -> None:
    client = TestClient(create_app(parse_service=StubParseFileErrorService()))

    response = client.post(
        "/v1/parse/file",
        files={"file": ("image.png", b"\x89PNG", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_source_type"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --extra dev pytest tests/api/test_parse_file_routes.py -v
```

Expected: FAIL because `parse_file_schemas` and `parse_file_routes` modules do not exist, and `create_app` does not accept `parse_service` with `parse_content`.

- [ ] **Step 3: Create parse file schemas**

Create `free_for_read/api/parse_file_schemas.py`:

```python
from pydantic import BaseModel


class ParseFilePathRequest(BaseModel):
    path: str
```

- [ ] **Step 4: Create parse file route**

Create `free_for_read/api/parse_file_routes.py`:

```python
from pathlib import Path

from fastapi import APIRouter, Request

from free_for_read.api.schemas import ParseResponse
from free_for_read.core.errors import ParseError


class ParseFileServiceProtocol:
    def parse_content(self, content: bytes, *, filename: str, source_url: str):
        raise NotImplementedError


def create_parse_file_router(parse_service: ParseFileServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post("/parse/file", response_model=ParseResponse)
    async def parse_file(request: Request):
        content_type = request.headers.get("content-type", "")
        source_url: str
        content: bytes

        if "multipart/form-data" in content_type:
            form = await request.form()
            upload = form.get("file")
            if upload is None:
                raise ParseError(
                    code="invalid_file_path",
                    message="No file field in multipart request.",
                )
            content = await upload.read()
            filename = getattr(upload, "filename", "upload") or "upload"
            source_url = f"file://{filename}"
        else:
            body = await request.json()
            file_path = body.get("path", "")

            resolved = Path(file_path).resolve()
            if ".." in Path(file_path).parts or not resolved.exists():
                raise ParseError(
                    code="invalid_file_path",
                    message="File path is invalid or does not exist.",
                    details={"path": file_path},
                )

            content = resolved.read_bytes()
            filename = resolved.name
            source_url = f"file://{resolved.as_posix()}"

        return parse_service.parse_content(
            content=content,
            filename=filename,
            source_url=source_url,
        )

    return router
```

- [ ] **Step 5: Update app.py to wire parse-file router**

Modify `free_for_read/api/app.py`:

Import section — add:

```python
from free_for_read.api.parse_file_routes import ParseFileServiceProtocol, create_parse_file_router
```

In `create_app()`, after the existing router includes, add:

```python
app.include_router(create_parse_file_router(service))
```

The full `create_app` signature and body becomes:

```python
def create_app(
    parse_service: ParseServiceProtocol | None = None,
    library_service: LibraryServiceProtocol | None = None,
    storage_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    root = storage_root or Path("storage")
    service = parse_service or ParseService()
    app.include_router(create_router(service))
    app.include_router(create_parse_file_router(service))
    library = library_service or LibraryService(
        storage=LocalStorageBackend(root=root),
        repository=SQLiteLibraryRepository(root / "library.sqlite3"),
    )
    library.initialize()
    app.include_router(create_library_router(library))
    # ... exception handlers and /health unchanged
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
uv run --extra dev pytest tests/api/test_parse_file_routes.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 7: Run linter and check existing tests**

Run:
```bash
uv run --extra dev ruff check free_for_read/api/parse_file_routes.py free_for_read/api/parse_file_schemas.py free_for_read/api/app.py tests/api/test_parse_file_routes.py
uv run --extra dev pytest tests/api/ -v
```

Expected: Linter PASS. All API tests PASS.

- [ ] **Step 8: Commit**

```bash
git add free_for_read/api/parse_file_schemas.py free_for_read/api/parse_file_routes.py free_for_read/api/app.py tests/api/test_parse_file_routes.py
git commit -m "feat: add local file parse route"
```

---

### Task 3: CLI Entry Point

**Files:**
- Create: `free_for_read/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/cli/__init__.py`
- Test: `tests/cli/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/cli/__init__.py`:

```python
```

Create `tests/cli/test_cli.py`:

```python
import json
import subprocess
import sys
import time

import httpx
import pytest


def test_cli_serve_prints_ready_line_and_responds_to_health() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "free_for_read.cli",
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        ready_line = process.stdout.readline().strip() if process.stdout else ""
        assert ready_line.startswith("READY http://127.0.0.1:"), f"Got: {ready_line}"

        port = int(ready_line.rsplit(":", 1)[-1])

        for _ in range(20):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
                break
            except httpx.ConnectError:
                time.sleep(0.05)
        else:
            raise AssertionError("Server did not become healthy")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_cli_respects_explicit_port() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "free_for_read.cli",
            "--port",
            "18765",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        ready_line = process.stdout.readline().strip() if process.stdout else ""
        assert ready_line == "READY http://127.0.0.1:18765", f"Got: {ready_line}"

        response = httpx.get("http://127.0.0.1:18765/health", timeout=5)
        assert response.status_code == 200
    finally:
        process.terminate()
        process.wait(timeout=5)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/cli/test_cli.py -v
```

Expected: FAIL because `free_for_read.cli` module does not exist or has no `__main__` behavior.

- [ ] **Step 3: Create CLI entry point**

Create `free_for_read/cli.py`:

```python
import argparse
import signal
import socket
import sys
from pathlib import Path

import uvicorn

from free_for_read.api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="free-for-read")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=0, help="Port to bind (0=ephemeral)")
    serve_parser.add_argument("--storage", default="storage", help="Storage root directory")

    args = parser.parse_args()

    if args.command == "serve":
        _serve(args.host, args.port, args.storage)
    else:
        parser.print_help()
        sys.exit(1)

    def _shutdown(signum, frame):
        sys.exit(0)


def _serve(host: str, port: int, storage_root: str) -> None:
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            port = s.getsockname()[1]

    app = create_app(storage_root=Path(storage_root))

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print(f"READY http://{host}:{port}", flush=True)

    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
```

Wait — `_shutdown` is defined inside `main()`, but used inside `_serve()`. Move it to module level:

Move `_shutdown` to module level:

```python
def _shutdown(signum, frame):
    sys.exit(0)


def _serve(host: str, port: int, storage_root: str) -> None:
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            port = s.getsockname()[1]

    app = create_app(storage_root=Path(storage_root))

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print(f"READY http://{host}:{port}", flush=True)

    uvicorn.run(app, host=host, port=port, log_config=None)
```

The full file:

```python
import argparse
import signal
import socket
import sys
from pathlib import Path

import uvicorn

from free_for_read.api.app import create_app


def _shutdown(signum, frame):
    sys.exit(0)


def _serve(host: str, port: int, storage_root: str) -> None:
    if port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            port = s.getsockname()[1]

    app = create_app(storage_root=Path(storage_root))

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print(f"READY http://{host}:{port}", flush=True)

    uvicorn.run(app, host=host, port=port, log_config=None)


def main() -> None:
    parser = argparse.ArgumentParser(prog="free-for-read")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=0, help="Port to bind (0=ephemeral)")
    serve_parser.add_argument("--storage", default="storage", help="Storage root directory")

    args = parser.parse_args()

    if args.command == "serve":
        _serve(args.host, args.port, args.storage)
    else:
        parser.print_help()
        sys.exit(1)
```

Also need a `__main__.py` for `python -m free_for_read.cli` to work (which the test in Step 1 uses):

Create `free_for_read/cli.py` as shown above. The `__main__.py` pattern is handled by `python -m free_for_read.cli` automatically since `free_for_read/cli.py` is a module with `if __name__ == "__main__": main()`.

But wait — the test uses `python -m free_for_read.cli`. For this to work, the CLI needs to run when executed as `__main__`. The `if __name__ == "__main__": main()` guard at the bottom handles this.

Actually, `python -m free_for_read.cli` executes `free_for_read/cli.py` as `__main__`, so the `if __name__ == "__main__"` guard will trigger.

- [ ] **Step 4: Add script entry point to pyproject.toml**

Modify `pyproject.toml` — add `[project.scripts]`:

```toml
[project.scripts]
free-for-read = "free_for_read.cli:main"
```

This enables `uv run free-for-read serve --port 0` after install.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --extra dev pytest tests/cli/test_cli.py -v
```

Expected: Both CLI tests PASS.

Note: the first test will start a real server subprocess and verify the READY line. The second test verifies explicit port binding.

- [ ] **Step 6: Run existing test suite and linter**

Run:
```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check free_for_read/cli.py tests/cli/
```

Expected: All tests PASS, linter PASS.

- [ ] **Step 7: Commit**

```bash
git add free_for_read/cli.py pyproject.toml tests/cli/
git commit -m "feat: add cli entry point"
```

---

### Task 4: Shutdown Endpoint

**Files:**
- Modify: `free_for_read/api/app.py`
- Test: `tests/api/test_shutdown.py`

- [ ] **Step 1: Write failing shutdown test**

Create `tests/api/test_shutdown.py`:

```python
from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def test_shutdown_returns_acknowledgement() -> None:
    client = TestClient(create_app())

    response = client.post("/shutdown")

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/api/test_shutdown.py::test_shutdown_returns_acknowledgement -v
```

Expected: FAIL with 404 (route not found) or 405 (method not allowed).

- [ ] **Step 3: Add shutdown endpoint to app.py**

Modify `free_for_read/api/app.py` — add the `/shutdown` route inside `create_app()`, before the `return app` line:

```python
    @app.post("/shutdown")
    async def shutdown():
        import asyncio
        import os
        import signal

        async def _delayed_exit():
            await asyncio.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        asyncio.create_task(_delayed_exit())
        return {"status": "shutting_down"}
```

- [ ] **Step 4: Run shutdown test**

Run:
```bash
uv run --extra dev pytest tests/api/test_shutdown.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all API tests and linter**

Run:
```bash
uv run --extra dev pytest tests/api/ -v
uv run --extra dev ruff check free_for_read/api/app.py tests/api/test_shutdown.py
```

Expected: All API tests PASS. Linter PASS.

- [ ] **Step 6: Commit**

```bash
git add free_for_read/api/app.py tests/api/test_shutdown.py
git commit -m "feat: add shutdown endpoint"
```

---

### Task 5: PyInstaller Packaging and Makefile

**Files:**
- Modify: `pyproject.toml`
- Create: `Makefile`

- [ ] **Step 1: Add PyInstaller dev dependency**

Modify `pyproject.toml` — add to `[project.optional-dependencies] dev`:

```toml
  "pyinstaller>=6.0",
```

Run:
```bash
uv lock
```

- [ ] **Step 2: Create Makefile**

Create `Makefile`:

```makefile
.PHONY: build build-macos build-linux build-windows clean

build:
	pyinstaller --onefile \
		--name free-for-read \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-macos:
	pyinstaller --onefile \
		--name free-for-read \
		--target-architecture universal2 \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-linux:
	pyinstaller --onefile \
		--name free-for-read \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-windows:
	pyinstaller --onefile \
		--name free-for-read \
		--noconsole \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

clean:
	rm -rf build/ dist/ *.spec
```

- [ ] **Step 3: Verify build succeeds**

Run:
```bash
make build
```

Expected: `dist/free-for-read` binary exists.

- [ ] **Step 4: Verify binary starts and responds**

Run:
```bash
./dist/free-for-read serve --port 0 &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:$(lsof -iTCP -sTCP:LISTEN -nP -p $SERVER_PID 2>/dev/null | grep -o '127.0.0.1:[0-9]*' | head -1 | cut -d: -f2)/health
kill $SERVER_PID
```

Manual verification: the binary starts, prints READY line, and the health endpoint responds.

- [ ] **Step 5: Commit**

```bash
git add Makefile pyproject.toml uv.lock
git commit -m "feat: add pyinstaller packaging"
```

---

### Task 6: Integration and Final Verification

**Files:**
- Create: `tests/api/test_parse_file_integration.py`
- Modify: `README.md`

- [ ] **Step 1: Write end-to-end integration test**

Create `tests/api/test_parse_file_integration.py`:

```python
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app


def build_minimal_epub() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
            <rootfiles><rootfile full-path="OPS/package.opf"/></rootfiles>
            </container>""",
        )
        archive.writestr(
            "OPS/package.opf",
            """<package xmlns="http://www.idpf.org/2007/opf"
            xmlns:dc="http://purl.org/dc/elements/1.1/">
            <metadata><dc:title>Test</dc:title></metadata>
            <manifest>
              <item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>
            </manifest>
            <spine><itemref idref="c1"/></spine>
            </package>""",
        )
        archive.writestr(
            "OPS/c1.xhtml",
            "<html><body><h1>Chapter</h1><p>Paragraph text.</p></body></html>",
        )
    return buffer.getvalue()


def test_parse_file_multipart_with_pdf_succeeds(tmp_path: Path) -> None:
    """Integration: parse a real PDF through the file route using multipart."""
    from io import BytesIO
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    pdf_bytes = buffer.getvalue()

    client = TestClient(create_app())

    response = client.post(
        "/v1/parse/file",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["source_type"] == "pdf"
    assert "---" in payload["markdown"]


def test_parse_file_path_mode_with_docx(tmp_path: Path) -> None:
    """Integration: parse a real DOCX through the file route using path mode."""
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_heading("Title", level=1)
    doc.add_paragraph("Body text.")
    file_path = tmp_path / "test.docx"
    doc.save(str(file_path))

    client = TestClient(create_app())

    response = client.post("/v1/parse/file", json={"path": str(file_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["source_type"] == "word"
    assert payload["markdown"] == "# Title\n\nBody text."


def test_parse_file_handles_storage_backed_import_and_parse(tmp_path: Path) -> None:
    """Integration: import an EPUB through library, then parse a chapter through file route."""
    client = TestClient(create_app(storage_root=tmp_path / "storage"))

    # Import an EPUB through library
    import_response = client.post(
        "/v1/books/import",
        files={"file": ("book.epub", build_minimal_epub(), "application/epub+zip")},
    )
    assert import_response.status_code == 200
    book_id = import_response.json()["book"]["id"]
    chapter_id = import_response.json()["chapters"][0]["id"]

    # Verify chapter is readable through library
    chapter = client.get(f"/v1/books/{book_id}/chapters/{chapter_id}")
    assert chapter.status_code == 200
    assert "# Chapter" in chapter.json()["markdown"]

    # Parse a new PDF through the file route — both routes coexist
    from pypdf import PdfWriter
    from io import BytesIO

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = BytesIO()
    writer.write(buf)

    parse_response = client.post(
        "/v1/parse/file",
        files={"file": ("doc.pdf", buf.getvalue(), "application/pdf")},
    )
    assert parse_response.status_code == 200
    assert parse_response.json()["metadata"]["source_type"] == "pdf"
```

- [ ] **Step 2: Run integration tests**

Run:
```bash
uv run --extra dev pytest tests/api/test_parse_file_integration.py -v
```

Expected: All 3 integration tests PASS.

- [ ] **Step 3: Update README with parse-file and CLI usage**

Modify `README.md` — add after the existing "Parse A URL" section:

```markdown
## Parse A Local File

```bash
curl -X POST http://127.0.0.1:8000/v1/parse/file \
  -F "file=@./document.pdf"
```

Or by local file path:

```bash
curl -X POST http://127.0.0.1:8000/v1/parse/file \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/alice/document.docx"}'
```

## CLI Server

```bash
free-for-read serve --port 0
```

Starts the API on an ephemeral port and prints `READY http://127.0.0.1:{port}` for sidecar orchestration.
```

- [ ] **Step 4: Run full test suite and linter**

Run:
```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
```

Expected: All tests PASS. Linter PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/api/test_parse_file_integration.py README.md
git commit -m "test: add parse file integration coverage and docs"
```

---

## Self-Review Notes

- Spec coverage: CLI (Task 3), `/v1/parse/file` multipart+path (Task 2), `/shutdown` (Task 4), PyInstaller packaging (Task 5), `parse_content` pipeline reuse (Task 1), Makefile (Task 5), README (Task 6). All spec requirements covered.
- Scope: No Tauri, no CI, no code signing — all deferred to Phase 4/6 per spec.
- Type consistency: `ParseResult` returned by `parse_content` matches `ParseResponse` schema. `ParseFileServiceProtocol` matches the real `ParseService` method signatures. CLI `create_app(storage_root=...)` passes through consistently.
- Placeholder check: All steps have complete code. No TBD or TODO markers.
