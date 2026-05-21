from pathlib import Path

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode, ParseMetadata, SourceType
from free_for_read.core.service import ParseResult


class StubParseFileService:
    def parse_content(self, content: bytes, *, source_url: str) -> ParseResult:
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
    def parse_content(self, content: bytes, *, source_url: str) -> ParseResult:
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
    # Create the file under a subdirectory of cwd (an allowed root)
    test_dir = Path.cwd() / "tmp_test_files"
    test_dir.mkdir(exist_ok=True)
    file_path = test_dir / "doc.html"
    file_path.write_text("<html>test</html>")

    client = TestClient(create_app(parse_service=StubParseFileService()))

    response = client.post("/v1/parse/file", json={"path": str(file_path)})

    assert response.status_code == 200
    assert response.json()["markdown"] == "# Test\n\nContent."

    # Cleanup
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)


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
