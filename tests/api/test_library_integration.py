from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def build_epub() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
            <container version="1.0"
              xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="OPS/package.opf"
                  media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>""",
        )
        archive.writestr(
            "OPS/package.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf"
              xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
              <metadata>
                <dc:title>Integration EPUB</dc:title>
                <dc:creator>Ada Writer</dc:creator>
              </metadata>
              <manifest>
                <item id="chapter"
                  href="chapter.xhtml"
                  media-type="application/xhtml+xml"/>
              </manifest>
              <spine>
                <itemref idref="chapter"/>
              </spine>
            </package>""",
        )
        archive.writestr(
            "OPS/chapter.xhtml",
            "<html><body><h1>Opening</h1><p>Hello integration.</p></body></html>",
        )
    return buffer.getvalue()


def test_import_epub_through_library_api(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    client = TestClient(create_app(library_service=service))

    imported = client.post(
        "/v1/books/import",
        files={"file": ("book.epub", build_epub(), "application/epub+zip")},
    )

    assert imported.status_code == 200
    import_payload = imported.json()
    book_id = import_payload["book"]["id"]
    chapter_id = import_payload["chapters"][0]["id"]

    books = client.get("/v1/books")
    assert books.status_code == 200
    assert [book["title"] for book in books.json()["items"]] == ["Integration EPUB"]

    chapter = client.get(f"/v1/books/{book_id}/chapters/{chapter_id}")
    assert chapter.status_code == 200
    assert chapter.json()["markdown"] == "# Opening\n\nHello integration."
