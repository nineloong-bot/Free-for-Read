# Ebook Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add EPUB, FB2, and FBZ import plus a persisted book library with chapters, progress, and bookmarks.

**Architecture:** Keep `/v1/parse` unchanged and add a separate library module. Ebook parsers produce chapter-level domain models, `LibraryService` orchestrates import and reads, `StorageBackend` hides file persistence, and `LibraryRepository` hides SQLite. The MVP uses local files and SQLite while preserving interface boundaries for future object storage and PostgreSQL.

**Tech Stack:** Python 3.10+, FastAPI multipart upload, Pydantic v2, `sqlite3`, `zipfile`, `defusedxml`, BeautifulSoup, pytest, pytest-httpx, ruff.

---

## File Structure

- Modify: `pyproject.toml`
  Add `defusedxml` and `python-multipart`.
- Modify: `.gitignore`
  Ignore local runtime storage and database files.
- Modify: `free_for_read/metadata/builder.py`
  Export `count_words()` so library code and existing metadata share one word counter.
- Create: `free_for_read/library/__init__.py`
  Package marker.
- Create: `free_for_read/library/models.py`
  Domain models for parsed ebooks, persisted books, chapters, progress, bookmarks, and paged results.
- Create: `free_for_read/parsers/ebooks.py`
  EPUB, FB2, and FBZ parsers plus parser selection by filename.
- Create: `free_for_read/library/storage.py`
  `StorageBackend` protocol and `LocalStorageBackend`.
- Create: `free_for_read/library/repository.py`
  `LibraryRepository` protocol and `SQLiteLibraryRepository`.
- Create: `free_for_read/library/service.py`
  Import, list, chapter lookup, progress, and bookmark orchestration.
- Create: `free_for_read/api/library_schemas.py`
  Request and response schemas for library routes.
- Create: `free_for_read/api/library_routes.py`
  `/v1/books` routes.
- Modify: `free_for_read/api/app.py`
  Wire the default library service and router.
- Modify: `README.md`
  Document local storage, import, and library endpoints.
- Create: `tests/parsers/test_ebooks_epub.py`
  EPUB parser tests and minimal EPUB fixture helpers.
- Create: `tests/parsers/test_ebooks_fb2.py`
  FB2 and FBZ parser tests.
- Create: `tests/library/test_storage.py`
  Local storage tests.
- Create: `tests/library/test_repository.py`
  SQLite repository tests.
- Create: `tests/library/test_service.py`
  Service orchestration tests.
- Create: `tests/api/test_library_routes.py`
  FastAPI library route tests.

---

### Task 1: Dependencies, Shared Word Count, and Library Models

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.gitignore`
- Modify: `free_for_read/metadata/builder.py`
- Create: `free_for_read/library/__init__.py`
- Create: `free_for_read/library/models.py`
- Test: `tests/library/test_models.py`
- Test: `tests/metadata/test_builder.py`

- [ ] **Step 1: Write failing model and word count tests**

Create `tests/library/test_models.py`:

```python
from datetime import datetime, timezone

from free_for_read.library.models import (
    Book,
    Bookmark,
    Chapter,
    EbookSourceType,
    ParsedChapter,
    ParsedEbook,
    ReadingProgress,
)


def test_parsed_ebook_counts_chapters_and_words() -> None:
    parsed = ParsedEbook(
        title="Example Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.EPUB,
        chapters=[
            ParsedChapter(
                index=0,
                title="Opening",
                markdown="Hello reader.",
                word_count=2,
                source_ref="chapters/opening.xhtml",
            ),
            ParsedChapter(
                index=1,
                title="Second",
                markdown="Another page.",
                word_count=2,
                source_ref="chapters/second.xhtml",
            ),
        ],
    )

    assert parsed.chapter_count == 2
    assert parsed.word_count == 4


def test_library_models_store_progress_and_bookmark_positions() -> None:
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    book = Book(
        id="book_1",
        title="Example Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.FB2,
        original_filename="example.fb2",
        storage_path="books/book_1/source.fb2",
        cover_path=None,
        word_count=10,
        chapter_count=1,
        created_at=now,
        updated_at=now,
    )
    chapter = Chapter(
        id="chapter_1",
        book_id=book.id,
        index=0,
        title="Opening",
        markdown="Hello reader.",
        word_count=2,
        source_ref="body/section[1]",
        metadata={"kind": "section"},
    )
    progress = ReadingProgress(
        book_id=book.id,
        chapter_id=chapter.id,
        position={"paragraph": 3, "offset": 12},
        updated_at=now,
    )
    bookmark = Bookmark(
        id="bookmark_1",
        book_id=book.id,
        chapter_id=chapter.id,
        position={"paragraph": 3, "offset": 12},
        label="Important",
        created_at=now,
    )

    assert book.source_type == EbookSourceType.FB2
    assert chapter.metadata == {"kind": "section"}
    assert progress.position["paragraph"] == 3
    assert bookmark.label == "Important"
```

Modify `tests/metadata/test_builder.py` with:

```python
from free_for_read.metadata.builder import count_words


def test_count_words_is_reusable_for_library_text() -> None:
    assert count_words("Hello reader. 你好 世界") == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/library/test_models.py tests/metadata/test_builder.py -v
```

Expected: FAIL because `free_for_read.library.models` and `count_words` do not exist.

- [ ] **Step 3: Add dependencies and ignore runtime storage**

Modify `pyproject.toml` dependencies:

```toml
  "defusedxml>=0.7.1",
  "python-multipart>=0.0.9",
```

Modify `.gitignore`:

```gitignore
storage/
*.sqlite
*.sqlite3
```

Run:

```bash
uv lock
```

Expected: `uv.lock` updates successfully.

- [ ] **Step 4: Export shared word counter**

Modify `free_for_read/metadata/builder.py`:

```python
def count_words(markdown: str) -> int:
    return len(WORD_RE.findall(markdown))
```

Change `build_metadata()` to call `count_words(markdown)`.

- [ ] **Step 5: Implement library models**

Create `free_for_read/library/__init__.py` as an empty package marker.

Create `free_for_read/library/models.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EbookSourceType(str, Enum):
    EPUB = "epub"
    FB2 = "fb2"
    FBZ = "fbz"


class ParsedChapter(BaseModel):
    index: int
    title: str
    markdown: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedEbook(BaseModel):
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    chapters: list[ParsedChapter]
    cover_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    @property
    def word_count(self) -> int:
        return sum(chapter.word_count for chapter in self.chapters)


class Book(BaseModel):
    id: str
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    original_filename: str
    storage_path: str
    cover_path: str | None = None
    word_count: int
    chapter_count: int
    created_at: datetime
    updated_at: datetime


class Chapter(BaseModel):
    id: str
    book_id: str
    index: int
    title: str
    markdown: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReadingProgress(BaseModel):
    book_id: str
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class Bookmark(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None
    created_at: datetime


class BookDetail(BaseModel):
    book: Book
    chapters: list[Chapter]
    progress: ReadingProgress | None = None
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
uv run --extra dev pytest tests/library/test_models.py tests/metadata/test_builder.py -v
```

Expected: PASS.

- [ ] **Step 7: Run linter**

Run:

```bash
uv run --extra dev ruff check .
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add .gitignore pyproject.toml uv.lock free_for_read/metadata/builder.py free_for_read/library/__init__.py free_for_read/library/models.py tests/library/test_models.py tests/metadata/test_builder.py
git commit -m "feat: add ebook library domain models"
```

---

### Task 2: EPUB Parser

**Files:**
- Create: `free_for_read/parsers/ebooks.py`
- Test: `tests/parsers/test_ebooks_epub.py`

- [ ] **Step 1: Write failing EPUB parser tests**

Create `tests/parsers/test_ebooks_epub.py`:

```python
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType
from free_for_read.parsers.ebooks import parse_epub


def build_epub(*, include_nav: bool = True) -> bytes:
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
        nav_item = (
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
            'properties="nav"/>'
            if include_nav
            else ""
        )
        archive.writestr(
            "OPS/package.opf",
            f"""<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf"
              xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
              <metadata>
                <dc:title>Sample EPUB</dc:title>
                <dc:creator>Ada Writer</dc:creator>
                <dc:language>en</dc:language>
              </metadata>
              <manifest>
                {nav_item}
                <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                <item id="c2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
              </manifest>
              <spine>
                <itemref idref="c1"/>
                <itemref idref="c2"/>
              </spine>
            </package>""",
        )
        if include_nav:
            archive.writestr(
                "OPS/nav.xhtml",
                """<html xmlns="http://www.w3.org/1999/xhtml">
                <body><nav epub:type="toc">
                <ol>
                  <li><a href="chapter1.xhtml">First Door</a></li>
                  <li><a href="chapter2.xhtml">Second Door</a></li>
                </ol>
                </nav></body></html>""",
            )
        archive.writestr(
            "OPS/chapter1.xhtml",
            "<html><body><h1>Ignored Heading</h1><p>Hello reader.</p></body></html>",
        )
        archive.writestr(
            "OPS/chapter2.xhtml",
            "<html><body><h1>Second Heading</h1><p>Another page.</p></body></html>",
        )
    return buffer.getvalue()


def test_parse_epub_uses_spine_order_and_nav_titles() -> None:
    parsed = parse_epub(build_epub(), filename="sample.epub")

    assert parsed.source_type == EbookSourceType.EPUB
    assert parsed.title == "Sample EPUB"
    assert parsed.author == "Ada Writer"
    assert parsed.language == "en"
    assert [chapter.title for chapter in parsed.chapters] == [
        "First Door",
        "Second Door",
    ]
    assert parsed.chapters[0].source_ref == "OPS/chapter1.xhtml"
    assert parsed.chapters[0].markdown == "# Ignored Heading\n\nHello reader."
    assert parsed.chapter_count == 2
    assert parsed.word_count == 7


def test_parse_epub_falls_back_to_first_heading_for_chapter_title() -> None:
    parsed = parse_epub(build_epub(include_nav=False), filename="sample.epub")

    assert [chapter.title for chapter in parsed.chapters] == [
        "Ignored Heading",
        "Second Heading",
    ]


def test_parse_epub_rejects_path_traversal_manifest_href() -> None:
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
            """<package xmlns="http://www.idpf.org/2007/opf">
            <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
              <dc:title>Bad</dc:title>
            </metadata>
            <manifest>
              <item id="c1" href="../secret.xhtml" media-type="application/xhtml+xml"/>
            </manifest>
            <spine><itemref idref="c1"/></spine>
            </package>""",
        )

    with pytest.raises(ParseError) as exc_info:
        parse_epub(buffer.getvalue(), filename="bad.epub")

    assert exc_info.value.code == "invalid_ebook"
```

- [ ] **Step 2: Run EPUB tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_epub.py -v
```

Expected: FAIL because `free_for_read.parsers.ebooks` does not exist.

- [ ] **Step 3: Implement minimal EPUB parser**

Create `free_for_read/parsers/ebooks.py` with:

```python
from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from bs4 import BeautifulSoup
from defusedxml import ElementTree

from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, DocumentNode
from free_for_read.library.models import EbookSourceType, ParsedChapter, ParsedEbook
from free_for_read.metadata.builder import count_words
from free_for_read.renderers.markdown import render_markdown


XML_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def parse_epub(content: bytes, *, filename: str) -> ParsedEbook:
    try:
        with ZipFile(BytesIO(content)) as archive:
            package_path = _epub_package_path(archive)
            package = _read_xml(archive, package_path)
            base_path = PurePosixPath(package_path).parent
            title = _xml_text(package, ".//dc:title") or _fallback_title(filename)
            author = _xml_text(package, ".//dc:creator")
            language = _xml_text(package, ".//dc:language")
            manifest = _epub_manifest(package)
            nav_titles = _epub_nav_titles(archive, package, base_path, manifest)
            chapters = _epub_chapters(archive, package, base_path, manifest, nav_titles)
    except ParseError:
        raise
    except (BadZipFile, ElementTree.ParseError, KeyError) as exc:
        raise ParseError(
            code="invalid_ebook",
            message="Invalid EPUB file.",
            details={"filename": filename},
        ) from exc
    return ParsedEbook(
        title=title,
        author=author,
        language=language,
        source_type=EbookSourceType.EPUB,
        chapters=chapters,
    )


def _epub_package_path(archive: ZipFile) -> str:
    container = _read_xml(archive, "META-INF/container.xml")
    rootfile = container.find(".//container:rootfile", XML_NS)
    if rootfile is None:
        raise ParseError(
            code="invalid_ebook",
            message="EPUB container does not declare a package file.",
        )
    return _safe_zip_path(rootfile.attrib.get("full-path", ""))


def _read_xml(archive: ZipFile, path: str) -> ElementTree.Element:
    with archive.open(path) as source:
        return ElementTree.fromstring(source.read())


def _xml_text(node: ElementTree.Element, path: str) -> str | None:
    found = node.find(path, XML_NS)
    if found is None or found.text is None:
        return None
    text = " ".join(found.text.split())
    return text or None


def _epub_manifest(package: ElementTree.Element) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    for item in package.findall(".//opf:manifest/opf:item", XML_NS):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        if item_id and href:
            manifest[item_id] = item.attrib
    return manifest


def _epub_nav_titles(
    archive: ZipFile,
    package: ElementTree.Element,
    base_path: PurePosixPath,
    manifest: dict[str, dict[str, str]],
) -> dict[str, str]:
    nav_href = None
    for item in manifest.values():
        if "nav" in item.get("properties", "").split():
            nav_href = item.get("href")
            break
    if not nav_href:
        return {}
    nav_path = _join_zip_path(base_path, nav_href)
    soup = BeautifulSoup(archive.read(nav_path), "html.parser")
    titles: dict[str, str] = {}
    for link in soup.find_all("a"):
        href = link.get("href")
        title = link.get_text(" ", strip=True)
        if href and title:
            chapter_path = _join_zip_path(base_path, href.split("#", 1)[0])
            titles[chapter_path] = title
    return titles


def _epub_chapters(
    archive: ZipFile,
    package: ElementTree.Element,
    base_path: PurePosixPath,
    manifest: dict[str, dict[str, str]],
    nav_titles: dict[str, str],
) -> list[ParsedChapter]:
    chapters: list[ParsedChapter] = []
    for itemref in package.findall(".//opf:spine/opf:itemref", XML_NS):
        item = manifest.get(itemref.attrib.get("idref", ""))
        if item is None:
            continue
        chapter_path = _join_zip_path(base_path, item["href"])
        document = _html_document(archive.read(chapter_path))
        markdown = render_markdown(document)
        title = nav_titles.get(chapter_path) or document.title or f"Chapter {len(chapters) + 1}"
        chapters.append(
            ParsedChapter(
                index=len(chapters),
                title=title,
                markdown=markdown,
                word_count=count_words(markdown),
                source_ref=chapter_path,
                metadata={"media_type": item.get("media-type")},
            )
        )
    if not chapters:
        raise ParseError(code="invalid_ebook", message="EPUB contains no readable chapters.")
    return chapters


def _html_document(content: bytes) -> Document:
    soup = BeautifulSoup(content, "html.parser")
    root = DocumentNode(type="document")
    title: str | None = None
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        if element.name and element.name.startswith("h"):
            level = int(element.name[1])
            if title is None:
                title = text
            root.children.append(DocumentNode(type="heading", text=text, level=level))
        else:
            root.children.append(DocumentNode(type="paragraph", text=text))
    return Document(root=root, title=title)


def _join_zip_path(base_path: PurePosixPath, href: str) -> str:
    return _safe_zip_path(str(base_path / href))


def _safe_zip_path(path: str) -> str:
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ParseError(
            code="invalid_ebook",
            message="Ebook contains an unsafe internal path.",
            details={"path": path},
        )
    return normalized.as_posix()


def _fallback_title(filename: str) -> str:
    return PurePosixPath(filename).stem or "Untitled"
```

- [ ] **Step 4: Run EPUB tests to verify they pass**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_epub.py -v
```

Expected: PASS.

- [ ] **Step 5: Run parser and lint checks**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_epub.py tests/renderers/test_markdown.py -v
uv run --extra dev ruff check free_for_read/parsers/ebooks.py tests/parsers/test_ebooks_epub.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add free_for_read/parsers/ebooks.py tests/parsers/test_ebooks_epub.py
git commit -m "feat: add epub parser"
```

---

### Task 3: FB2 and FBZ Parsers

**Files:**
- Modify: `free_for_read/parsers/ebooks.py`
- Test: `tests/parsers/test_ebooks_fb2.py`

- [ ] **Step 1: Write failing FB2 and FBZ tests**

Create `tests/parsers/test_ebooks_fb2.py`:

```python
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType
from free_for_read.parsers.ebooks import parse_ebook, parse_fb2, parse_fbz


FB2_TEXT = """<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <genre>sf</genre>
      <author><first-name>Ada</first-name><last-name>Writer</last-name></author>
      <book-title>Sample FB2</book-title>
      <lang>en</lang>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Opening</p></title>
      <p>Hello reader.</p>
      <p>Welcome home.</p>
    </section>
    <section>
      <title><p>Second</p></title>
      <p>Another page.</p>
    </section>
  </body>
</FictionBook>
"""


def build_fbz() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("book.fb2", FB2_TEXT.encode("utf-8"))
    return buffer.getvalue()


def test_parse_fb2_maps_metadata_and_sections_to_chapters() -> None:
    parsed = parse_fb2(FB2_TEXT.encode("utf-8"), filename="sample.fb2")

    assert parsed.source_type == EbookSourceType.FB2
    assert parsed.title == "Sample FB2"
    assert parsed.author == "Ada Writer"
    assert parsed.language == "en"
    assert [chapter.title for chapter in parsed.chapters] == ["Opening", "Second"]
    assert parsed.chapters[0].markdown == "# Opening\n\nHello reader.\n\nWelcome home."
    assert parsed.chapters[1].source_ref == "body/section[2]"


def test_parse_fbz_delegates_to_first_safe_fb2_entry() -> None:
    parsed = parse_fbz(build_fbz(), filename="sample.fbz")

    assert parsed.source_type == EbookSourceType.FBZ
    assert parsed.title == "Sample FB2"
    assert parsed.chapters[0].title == "Opening"


def test_parse_ebook_dispatches_by_filename() -> None:
    parsed = parse_ebook(FB2_TEXT.encode("utf-8"), filename="sample.fb2")

    assert parsed.source_type == EbookSourceType.FB2


def test_parse_fbz_rejects_archive_without_fb2() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("readme.txt", "not a book")

    with pytest.raises(ParseError) as exc_info:
        parse_fbz(buffer.getvalue(), filename="empty.fbz")

    assert exc_info.value.code == "invalid_ebook"


def test_parse_ebook_rejects_unsupported_extension() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_ebook(b"content", filename="sample.mobi")

    assert exc_info.value.code == "unsupported_ebook_format"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_fb2.py -v
```

Expected: FAIL because `parse_fb2`, `parse_fbz`, and `parse_ebook` do not exist.

- [ ] **Step 3: Implement FB2, FBZ, and dispatch functions**

Modify `free_for_read/parsers/ebooks.py`:

```python
def parse_ebook(content: bytes, *, filename: str) -> ParsedEbook:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix == ".epub":
        return parse_epub(content, filename=filename)
    if suffix == ".fb2":
        return parse_fb2(content, filename=filename)
    if suffix == ".fbz":
        return parse_fbz(content, filename=filename)
    raise ParseError(
        code="unsupported_ebook_format",
        message="Unsupported ebook format.",
        details={"filename": filename},
    )


def parse_fb2(content: bytes, *, filename: str) -> ParsedEbook:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ParseError(
            code="invalid_ebook",
            message="Invalid FB2 file.",
            details={"filename": filename},
        ) from exc
    ns = {"fb2": root.tag.split("}", 1)[0].strip("{")} if root.tag.startswith("{") else {}
    title = _fb2_text(root, ".//fb2:book-title", ns) or _fallback_title(filename)
    language = _fb2_text(root, ".//fb2:lang", ns)
    author = _fb2_author(root, ns)
    chapters = _fb2_chapters(root, ns)
    return ParsedEbook(
        title=title,
        author=author,
        language=language,
        source_type=EbookSourceType.FB2,
        chapters=chapters,
    )


def parse_fbz(content: bytes, *, filename: str) -> ParsedEbook:
    try:
        with ZipFile(BytesIO(content)) as archive:
            fb2_names = [
                name for name in archive.namelist()
                if name.lower().endswith(".fb2") and not PurePosixPath(name).is_absolute()
            ]
            safe_names = [name for name in fb2_names if ".." not in PurePosixPath(name).parts]
            if not safe_names:
                raise ParseError(
                    code="invalid_ebook",
                    message="FBZ archive does not contain a safe FB2 file.",
                    details={"filename": filename},
                )
            parsed = parse_fb2(archive.read(safe_names[0]), filename=safe_names[0])
    except ParseError:
        raise
    except BadZipFile as exc:
        raise ParseError(
            code="invalid_ebook",
            message="Invalid FBZ file.",
            details={"filename": filename},
        ) from exc
    return parsed.model_copy(update={"source_type": EbookSourceType.FBZ})


def _fb2_text(root: ElementTree.Element, path: str, ns: dict[str, str]) -> str | None:
    found = root.find(path, ns)
    if found is None:
        return None
    text = " ".join("".join(found.itertext()).split())
    return text or None


def _fb2_author(root: ElementTree.Element, ns: dict[str, str]) -> str | None:
    author = root.find(".//fb2:title-info/fb2:author", ns)
    if author is None:
        return None
    parts = [
        _fb2_text(author, "fb2:first-name", ns),
        _fb2_text(author, "fb2:middle-name", ns),
        _fb2_text(author, "fb2:last-name", ns),
    ]
    joined = " ".join(part for part in parts if part)
    return joined or None


def _fb2_chapters(root: ElementTree.Element, ns: dict[str, str]) -> list[ParsedChapter]:
    sections = root.findall("./fb2:body/fb2:section", ns)
    chapters: list[ParsedChapter] = []
    for index, section in enumerate(sections):
        title = _fb2_text(section, "fb2:title", ns) or f"Chapter {index + 1}"
        paragraphs = [_fb2_text(paragraph, ".", ns) for paragraph in section.findall("fb2:p", ns)]
        body = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
        markdown = f"# {title}" if not body else f"# {title}\n\n{body}"
        chapters.append(
            ParsedChapter(
                index=index,
                title=title,
                markdown=markdown,
                word_count=count_words(markdown),
                source_ref=f"body/section[{index + 1}]",
            )
        )
    if not chapters:
        raise ParseError(code="invalid_ebook", message="FB2 contains no readable chapters.")
    return chapters
```

Keep the existing `_fallback_title()` and `_safe_zip_path()` helpers from Task 2.
Do not create duplicate helpers with the same behavior.

- [ ] **Step 4: Run FB2 tests to verify they pass**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_fb2.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all ebook parser tests and lint**

Run:

```bash
uv run --extra dev pytest tests/parsers/test_ebooks_epub.py tests/parsers/test_ebooks_fb2.py -v
uv run --extra dev ruff check free_for_read/parsers/ebooks.py tests/parsers/test_ebooks_epub.py tests/parsers/test_ebooks_fb2.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add free_for_read/parsers/ebooks.py tests/parsers/test_ebooks_fb2.py
git commit -m "feat: add fb2 and fbz parsers"
```

---

### Task 4: Local Storage Backend

**Files:**
- Create: `free_for_read/library/storage.py`
- Test: `tests/library/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/library/test_storage.py`:

```python
import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.storage import LocalStorageBackend


def test_local_storage_saves_file_with_unique_safe_name(tmp_path) -> None:
    storage = LocalStorageBackend(root=tmp_path)

    first = storage.save("My Book.epub", b"first")
    second = storage.save("My Book.epub", b"second")

    assert first != second
    assert (tmp_path / first).read_bytes() == b"first"
    assert (tmp_path / second).read_bytes() == b"second"
    assert first.endswith(".epub")
    assert second.endswith(".epub")


def test_local_storage_rejects_unsafe_filename(tmp_path) -> None:
    storage = LocalStorageBackend(root=tmp_path)

    with pytest.raises(ParseError) as exc_info:
        storage.save("../secret.epub", b"content")

    assert exc_info.value.code == "storage_failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/library/test_storage.py -v
```

Expected: FAIL because `free_for_read.library.storage` does not exist.

- [ ] **Step 3: Implement storage backend**

Create `free_for_read/library/storage.py`:

```python
from pathlib import Path, PurePath
from typing import Protocol
from uuid import uuid4

from free_for_read.core.errors import ParseError


class StorageBackend(Protocol):
    def save(self, filename: str, content: bytes) -> str:
        raise NotImplementedError


class LocalStorageBackend:
    def __init__(self, *, root: Path | str = "storage") -> None:
        self.root = Path(root)

    def save(self, filename: str, content: bytes) -> str:
        safe_name = _safe_filename(filename)
        self.root.mkdir(parents=True, exist_ok=True)
        suffix = Path(safe_name).suffix.lower()
        stem = Path(safe_name).stem.replace(" ", "_") or "book"
        key = f"books/{uuid4().hex}_{stem}{suffix}"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(content)
        except OSError as exc:
            raise ParseError(
                code="storage_failed",
                message="Failed to save uploaded file.",
                details={"filename": filename},
            ) from exc
        return key


def _safe_filename(filename: str) -> str:
    path = PurePath(filename)
    if path.name != filename or not path.name:
        raise ParseError(
            code="storage_failed",
            message="Unsafe upload filename.",
            details={"filename": filename},
        )
    return path.name
```

- [ ] **Step 4: Run storage tests**

Run:

```bash
uv run --extra dev pytest tests/library/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Run lint**

Run:

```bash
uv run --extra dev ruff check free_for_read/library/storage.py tests/library/test_storage.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add free_for_read/library/storage.py tests/library/test_storage.py
git commit -m "feat: add local ebook storage"
```

---

### Task 5: SQLite Library Repository

**Files:**
- Create: `free_for_read/library/repository.py`
- Test: `tests/library/test_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/library/test_repository.py`:

```python
from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType, ParsedChapter, ParsedEbook
from free_for_read.library.repository import SQLiteLibraryRepository


def sample_parsed_book() -> ParsedEbook:
    return ParsedEbook(
        title="Stored Book",
        author="Ada",
        language="en",
        source_type=EbookSourceType.EPUB,
        chapters=[
            ParsedChapter(
                index=0,
                title="Opening",
                markdown="# Opening\n\nHello reader.",
                word_count=3,
                source_ref="chapter1.xhtml",
            ),
            ParsedChapter(
                index=1,
                title="Second",
                markdown="# Second\n\nAnother page.",
                word_count=3,
                source_ref="chapter2.xhtml",
            ),
        ],
    )


def test_repository_inserts_and_fetches_book_with_ordered_chapters(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()

    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    listed = repository.list_books(limit=10, offset=0)
    fetched = repository.get_book(detail.book.id)
    chapters = repository.list_chapters(detail.book.id)

    assert listed[0].id == detail.book.id
    assert fetched.book.title == "Stored Book"
    assert [chapter.title for chapter in chapters] == ["Opening", "Second"]
    assert fetched.chapters[1].markdown == "# Second\n\nAnother page."


def test_repository_upserts_progress(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    progress = repository.upsert_progress(
        book_id=detail.book.id,
        chapter_id=detail.chapters[0].id,
        position={"paragraph": 1},
    )
    updated = repository.upsert_progress(
        book_id=detail.book.id,
        chapter_id=detail.chapters[1].id,
        position={"paragraph": 2},
    )

    assert progress.book_id == detail.book.id
    assert updated.chapter_id == detail.chapters[1].id
    assert repository.get_progress(detail.book.id).position == {"paragraph": 2}


def test_repository_creates_lists_and_deletes_bookmarks(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()
    detail = repository.create_book(
        parsed=sample_parsed_book(),
        original_filename="stored.epub",
        storage_path="books/stored.epub",
    )

    bookmark = repository.create_bookmark(
        book_id=detail.book.id,
        chapter_id=detail.chapters[0].id,
        position={"paragraph": 1},
        label="Start",
    )

    assert repository.list_bookmarks(detail.book.id)[0].label == "Start"
    repository.delete_bookmark(detail.book.id, bookmark.id)
    assert repository.list_bookmarks(detail.book.id) == []


def test_repository_raises_for_missing_book(tmp_path) -> None:
    repository = SQLiteLibraryRepository(tmp_path / "library.sqlite3")
    repository.initialize()

    try:
        repository.get_book("missing")
    except ParseError as exc:
        assert exc.code == "book_not_found"
    else:
        raise AssertionError("missing book should raise ParseError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/library/test_repository.py -v
```

Expected: FAIL because `free_for_read.library.repository` does not exist.

- [ ] **Step 3: Implement repository schema and CRUD**

Create `free_for_read/library/repository.py`. Implement:

```python
class LibraryRepository(Protocol):
    def initialize(self) -> None:
        raise NotImplementedError

    def create_book(
        self, *, parsed: ParsedEbook, original_filename: str, storage_path: str
    ) -> BookDetail:
        raise NotImplementedError

    def list_books(self, *, limit: int, offset: int) -> list[Book]:
        raise NotImplementedError

    def get_book(self, book_id: str) -> BookDetail:
        raise NotImplementedError

    def list_chapters(self, book_id: str) -> list[Chapter]:
        raise NotImplementedError

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        raise NotImplementedError

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        raise NotImplementedError

    def upsert_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        raise NotImplementedError

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        raise NotImplementedError

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        raise NotImplementedError

    def delete_bookmark(self, book_id: str, bookmark_id: str) -> None:
        raise NotImplementedError
```

Use these table names and columns:

```sql
CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  language TEXT,
  source_type TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  cover_path TEXT,
  word_count INTEGER NOT NULL,
  chapter_count INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  chapter_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  markdown TEXT NOT NULL,
  word_count INTEGER NOT NULL,
  source_ref TEXT NOT NULL,
  metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reading_progress (
  book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  position_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookmarks (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  position_json TEXT NOT NULL,
  label TEXT,
  created_at TEXT NOT NULL
);
```

Generate ids with `uuid4().hex` prefixed as `book_`, `chapter_`, and `bookmark_`.
Store datetimes as UTC ISO 8601 strings. Wrap `sqlite3.Error` as `ParseError` with
code `repository_failed`.

- [ ] **Step 4: Run repository tests**

Run:

```bash
uv run --extra dev pytest tests/library/test_repository.py -v
```

Expected: PASS.

- [ ] **Step 5: Run lint**

Run:

```bash
uv run --extra dev ruff check free_for_read/library/repository.py tests/library/test_repository.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add free_for_read/library/repository.py tests/library/test_repository.py
git commit -m "feat: add sqlite ebook repository"
```

---

### Task 6: Library Service

**Files:**
- Create: `free_for_read/library/service.py`
- Test: `tests/library/test_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/library/test_service.py`:

```python
from pathlib import Path

import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.models import EbookSourceType, ParsedChapter, ParsedEbook
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def test_library_service_imports_and_lists_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
        parser=lambda content, filename: ParsedEbook(
            title="Service Book",
            author="Ada",
            language="en",
            source_type=EbookSourceType.EPUB,
            chapters=[
                ParsedChapter(
                    index=0,
                    title="Opening",
                    markdown="# Opening\n\nHello.",
                    word_count=2,
                    source_ref="chapter.xhtml",
                )
            ],
        ),
    )
    service.initialize()

    detail = service.import_book(filename="service.epub", content=b"epub bytes")

    assert detail.book.title == "Service Book"
    assert service.list_books(limit=10, offset=0)[0].id == detail.book.id
    assert Path(tmp_path / "storage" / detail.book.storage_path).exists()


def test_library_service_validates_progress_chapter_belongs_to_book(tmp_path) -> None:
    service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    service.initialize()

    with pytest.raises(ParseError) as exc_info:
        service.update_progress(
            book_id="missing",
            chapter_id="chapter_missing",
            position={"paragraph": 1},
        )

    assert exc_info.value.code == "book_not_found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/library/test_service.py -v
```

Expected: FAIL because `free_for_read.library.service` does not exist.

- [ ] **Step 3: Implement service orchestration**

Create `free_for_read/library/service.py`:

```python
from collections.abc import Callable

from free_for_read.library.models import Book, BookDetail, Bookmark, Chapter, ParsedEbook, ReadingProgress
from free_for_read.library.repository import LibraryRepository
from free_for_read.library.storage import StorageBackend
from free_for_read.parsers.ebooks import parse_ebook


EbookParser = Callable[[bytes, str], ParsedEbook]


class LibraryService:
    def __init__(
        self,
        *,
        storage: StorageBackend,
        repository: LibraryRepository,
        parser: EbookParser | None = None,
    ) -> None:
        self.storage = storage
        self.repository = repository
        self.parser = parser or (lambda content, filename: parse_ebook(content, filename=filename))

    def initialize(self) -> None:
        self.repository.initialize()

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        parsed = self.parser(content, filename)
        storage_path = self.storage.save(filename, content)
        return self.repository.create_book(
            parsed=parsed,
            original_filename=filename,
            storage_path=storage_path,
        )

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        return self.repository.list_books(limit=limit, offset=offset)

    def get_book(self, book_id: str) -> BookDetail:
        return self.repository.get_book(book_id)

    def list_chapters(self, book_id: str) -> list[Chapter]:
        return self.repository.list_chapters(book_id)

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        return self.repository.get_chapter(book_id, chapter_id)

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        self.repository.get_book(book_id)
        return self.repository.get_progress(book_id)

    def update_progress(
        self, *, book_id: str, chapter_id: str, position: dict
    ) -> ReadingProgress:
        self.repository.get_chapter(book_id, chapter_id)
        return self.repository.upsert_progress(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
        )

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict,
        label: str | None,
    ) -> Bookmark:
        self.repository.get_chapter(book_id, chapter_id)
        return self.repository.create_bookmark(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            label=label,
        )

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        self.repository.get_book(book_id)
        return self.repository.list_bookmarks(book_id)

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        self.repository.get_book(book_id)
        self.repository.delete_bookmark(book_id, bookmark_id)
```

Keep imports formatted by ruff. If the long import line exceeds 100 characters,
split it across parentheses.

- [ ] **Step 4: Run service tests**

Run:

```bash
uv run --extra dev pytest tests/library/test_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Run related tests and lint**

Run:

```bash
uv run --extra dev pytest tests/library/test_repository.py tests/library/test_storage.py tests/library/test_service.py -v
uv run --extra dev ruff check free_for_read/library tests/library
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add free_for_read/library/service.py tests/library/test_service.py
git commit -m "feat: add ebook library service"
```

---

### Task 7: Library API Routes and App Wiring

**Files:**
- Create: `free_for_read/api/library_schemas.py`
- Create: `free_for_read/api/library_routes.py`
- Modify: `free_for_read/api/app.py`
- Test: `tests/api/test_library_routes.py`
- Test: `tests/api/test_app.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/api/test_library_routes.py`:

```python
from typing import Any

from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.library.models import (
    Book,
    BookDetail,
    Bookmark,
    Chapter,
    EbookSourceType,
    ReadingProgress,
)


class StubLibraryService:
    def __init__(self) -> None:
        self.book = Book(
            id="book_1",
            title="API Book",
            author="Ada",
            language="en",
            source_type=EbookSourceType.EPUB,
            original_filename="api.epub",
            storage_path="books/api.epub",
            cover_path=None,
            word_count=2,
            chapter_count=1,
            created_at="2026-05-20T00:00:00+00:00",
            updated_at="2026-05-20T00:00:00+00:00",
        )
        self.chapter = Chapter(
            id="chapter_1",
            book_id="book_1",
            index=0,
            title="Opening",
            markdown="# Opening\n\nHello.",
            word_count=2,
            source_ref="chapter.xhtml",
        )
        self.progress: ReadingProgress | None = None
        self.bookmarks: list[Bookmark] = []

    def initialize(self) -> None:
        return None

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        assert filename == "api.epub"
        assert content == b"epub bytes"
        return BookDetail(book=self.book, chapters=[self.chapter])

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        assert limit == 50
        assert offset == 0
        return [self.book]

    def get_book(self, book_id: str) -> BookDetail:
        assert book_id == "book_1"
        return BookDetail(book=self.book, chapters=[self.chapter], progress=self.progress)

    def list_chapters(self, book_id: str) -> list[Chapter]:
        assert book_id == "book_1"
        return [self.chapter]

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        assert book_id == "book_1"
        assert chapter_id == "chapter_1"
        return self.chapter

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        assert book_id == "book_1"
        return self.progress

    def update_progress(
        self, *, book_id: str, chapter_id: str, position: dict[str, Any]
    ) -> ReadingProgress:
        self.progress = ReadingProgress(
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            updated_at="2026-05-20T00:00:00+00:00",
        )
        return self.progress

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict[str, Any],
        label: str | None,
    ) -> Bookmark:
        bookmark = Bookmark(
            id="bookmark_1",
            book_id=book_id,
            chapter_id=chapter_id,
            position=position,
            label=label,
            created_at="2026-05-20T00:00:00+00:00",
        )
        self.bookmarks.append(bookmark)
        return bookmark

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        assert book_id == "book_1"
        return self.bookmarks

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        assert book_id == "book_1"
        assert bookmark_id == "bookmark_1"
        self.bookmarks = []


def test_import_book_route_returns_book_detail() -> None:
    client = TestClient(create_app(library_service=StubLibraryService()))

    response = client.post(
        "/v1/books/import",
        files={"file": ("api.epub", b"epub bytes", "application/epub+zip")},
    )

    assert response.status_code == 200
    assert response.json()["book"]["title"] == "API Book"
    assert response.json()["chapters"][0]["title"] == "Opening"
    assert "markdown" not in response.json()["chapters"][0]


def test_book_chapter_progress_and_bookmark_routes() -> None:
    service = StubLibraryService()
    client = TestClient(create_app(library_service=service))

    assert client.get("/v1/books").json()["items"][0]["id"] == "book_1"
    assert client.get("/v1/books/book_1").json()["book"]["id"] == "book_1"
    assert client.get("/v1/books/book_1/chapters").json()["items"][0]["id"] == "chapter_1"
    assert (
        client.get("/v1/books/book_1/chapters/chapter_1").json()["markdown"]
        == "# Opening\n\nHello."
    )

    progress = client.put(
        "/v1/books/book_1/progress",
        json={"chapter_id": "chapter_1", "position": {"paragraph": 1}},
    )
    assert progress.json()["position"] == {"paragraph": 1}
    assert client.get("/v1/books/book_1/progress").json()["chapter_id"] == "chapter_1"

    bookmark = client.post(
        "/v1/books/book_1/bookmarks",
        json={"chapter_id": "chapter_1", "position": {"paragraph": 1}, "label": "Start"},
    )
    assert bookmark.json()["label"] == "Start"
    assert client.get("/v1/books/book_1/bookmarks").json()["items"][0]["id"] == "bookmark_1"
    assert client.delete("/v1/books/book_1/bookmarks/bookmark_1").status_code == 204
```

Modify `tests/api/test_app.py` with a temp-backed app construction test:

```python
def test_create_app_accepts_library_service() -> None:
    app = create_app(library_service=StubLibraryService())

    assert app.title == "Free for Read"
```

Add this tiny service inside `tests/api/test_app.py` before the new test:

```python
class StubLibraryService:
    def initialize(self) -> None:
        return None
```

- [ ] **Step 2: Run route tests to verify they fail**

Run:

```bash
uv run --extra dev pytest tests/api/test_library_routes.py tests/api/test_app.py -v
```

Expected: FAIL because `library_service` app wiring and library routes do not exist.

- [ ] **Step 3: Implement API schemas**

Create `free_for_read/api/library_schemas.py`:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from free_for_read.library.models import EbookSourceType


class BookResponse(BaseModel):
    id: str
    title: str
    author: str | None = None
    language: str | None = None
    source_type: EbookSourceType
    original_filename: str
    cover_path: str | None = None
    word_count: int
    chapter_count: int
    created_at: datetime
    updated_at: datetime


class ChapterSummaryResponse(BaseModel):
    id: str
    book_id: str
    index: int
    title: str
    word_count: int
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChapterResponse(ChapterSummaryResponse):
    markdown: str
    previous_chapter_id: str | None = None
    next_chapter_id: str | None = None


class ProgressRequest(BaseModel):
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)


class ProgressResponse(BaseModel):
    book_id: str
    chapter_id: str
    position: dict[str, Any]
    updated_at: datetime


class BookmarkRequest(BaseModel):
    chapter_id: str
    position: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None


class BookmarkResponse(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    position: dict[str, Any]
    label: str | None = None
    created_at: datetime


class BookDetailResponse(BaseModel):
    book: BookResponse
    chapters: list[ChapterSummaryResponse]
    progress: ProgressResponse | None = None


class BookListResponse(BaseModel):
    items: list[BookResponse]
    limit: int
    offset: int


class ChapterListResponse(BaseModel):
    items: list[ChapterSummaryResponse]


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
```

- [ ] **Step 4: Implement routes and app wiring**

Create `free_for_read/api/library_routes.py`:

```python
from typing import Protocol

from fastapi import APIRouter, File, UploadFile
from starlette import status

from free_for_read.api.library_schemas import (
    BookDetailResponse,
    BookListResponse,
    BookmarkListResponse,
    BookmarkRequest,
    BookmarkResponse,
    ChapterListResponse,
    ChapterResponse,
    ProgressRequest,
    ProgressResponse,
)
from free_for_read.library.models import Book, BookDetail, Bookmark, Chapter, ReadingProgress


class LibraryServiceProtocol(Protocol):
    def initialize(self) -> None:
        raise NotImplementedError

    def import_book(self, *, filename: str, content: bytes) -> BookDetail:
        raise NotImplementedError

    def list_books(self, *, limit: int = 50, offset: int = 0) -> list[Book]:
        raise NotImplementedError

    def get_book(self, book_id: str) -> BookDetail:
        raise NotImplementedError

    def list_chapters(self, book_id: str) -> list[Chapter]:
        raise NotImplementedError

    def get_chapter(self, book_id: str, chapter_id: str) -> Chapter:
        raise NotImplementedError

    def get_progress(self, book_id: str) -> ReadingProgress | None:
        raise NotImplementedError

    def update_progress(
        self, *, book_id: str, chapter_id: str, position: dict
    ) -> ReadingProgress:
        raise NotImplementedError

    def create_bookmark(
        self,
        *,
        book_id: str,
        chapter_id: str,
        position: dict,
        label: str | None,
    ) -> Bookmark:
        raise NotImplementedError

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        raise NotImplementedError

    def delete_bookmark(self, *, book_id: str, bookmark_id: str) -> None:
        raise NotImplementedError


def create_library_router(service: LibraryServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1/books")

    @router.post("/import", response_model=BookDetailResponse)
    async def import_book(file: UploadFile = File(...)) -> BookDetail:
        content = await file.read()
        return service.import_book(filename=file.filename or "upload", content=content)

    @router.get("", response_model=BookListResponse)
    def list_books(limit: int = 50, offset: int = 0) -> dict:
        return {"items": service.list_books(limit=limit, offset=offset), "limit": limit, "offset": offset}

    @router.get("/{book_id}", response_model=BookDetailResponse)
    def get_book(book_id: str) -> BookDetail:
        return service.get_book(book_id)

    @router.get("/{book_id}/chapters", response_model=ChapterListResponse)
    def list_chapters(book_id: str) -> dict:
        return {"items": service.list_chapters(book_id)}

    @router.get("/{book_id}/chapters/{chapter_id}", response_model=ChapterResponse)
    def get_chapter(book_id: str, chapter_id: str) -> dict:
        chapters = service.list_chapters(book_id)
        chapter = service.get_chapter(book_id, chapter_id)
        ids = [item.id for item in chapters]
        current = ids.index(chapter.id)
        previous_id = ids[current - 1] if current > 0 else None
        next_id = ids[current + 1] if current + 1 < len(ids) else None
        return {
            **chapter.model_dump(),
            "previous_chapter_id": previous_id,
            "next_chapter_id": next_id,
        }

    @router.get("/{book_id}/progress", response_model=ProgressResponse | None)
    def get_progress(book_id: str) -> ReadingProgress | None:
        return service.get_progress(book_id)

    @router.put("/{book_id}/progress", response_model=ProgressResponse)
    def update_progress(book_id: str, request: ProgressRequest) -> ReadingProgress:
        return service.update_progress(
            book_id=book_id,
            chapter_id=request.chapter_id,
            position=request.position,
        )

    @router.post("/{book_id}/bookmarks", response_model=BookmarkResponse)
    def create_bookmark(book_id: str, request: BookmarkRequest) -> Bookmark:
        return service.create_bookmark(
            book_id=book_id,
            chapter_id=request.chapter_id,
            position=request.position,
            label=request.label,
        )

    @router.get("/{book_id}/bookmarks", response_model=BookmarkListResponse)
    def list_bookmarks(book_id: str) -> dict:
        return {"items": service.list_bookmarks(book_id)}

    @router.delete(
        "/{book_id}/bookmarks/{bookmark_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_bookmark(book_id: str, bookmark_id: str) -> None:
        service.delete_bookmark(book_id=book_id, bookmark_id=bookmark_id)

    return router
```

Modify `free_for_read/api/app.py` so `create_app()` accepts `library_service`:

```python
from pathlib import Path

from free_for_read.api.library_routes import LibraryServiceProtocol, create_library_router
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.service import LibraryService
from free_for_read.library.storage import LocalStorageBackend


def create_app(
    parse_service: ParseServiceProtocol | None = None,
    library_service: LibraryServiceProtocol | None = None,
) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    service = parse_service or ParseService()
    app.include_router(create_router(service))
    library = library_service or LibraryService(
        storage=LocalStorageBackend(root=Path("storage")),
        repository=SQLiteLibraryRepository(Path("storage") / "library.sqlite3"),
    )
    library.initialize()
    app.include_router(create_library_router(library))
```

Keep existing exception handlers and `/health` unchanged.

- [ ] **Step 5: Run API tests**

Run:

```bash
uv run --extra dev pytest tests/api/test_library_routes.py tests/api/test_app.py -v
```

Expected: PASS.

- [ ] **Step 6: Run API lint**

Run:

```bash
uv run --extra dev ruff check free_for_read/api tests/api
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add free_for_read/api/app.py free_for_read/api/library_routes.py free_for_read/api/library_schemas.py tests/api/test_library_routes.py tests/api/test_app.py
git commit -m "feat: add ebook library api"
```

---

### Task 8: End-to-End Integration, README, and Final Verification

**Files:**
- Modify: `README.md`
- Test: `tests/api/test_library_integration.py`

- [ ] **Step 1: Write failing end-to-end import test**

Create `tests/api/test_library_integration.py`:

```python
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
            <metadata>
              <dc:title>Integration Book</dc:title>
              <dc:creator>Ada</dc:creator>
              <dc:language>en</dc:language>
            </metadata>
            <manifest>
              <item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/>
            </manifest>
            <spine><itemref idref="c1"/></spine>
            </package>""",
        )
        archive.writestr(
            "OPS/chapter.xhtml",
            "<html><body><h1>Opening</h1><p>Hello integration.</p></body></html>",
        )
    return buffer.getvalue()


def test_imported_epub_is_available_through_library_routes(tmp_path) -> None:
    library_service = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=SQLiteLibraryRepository(tmp_path / "library.sqlite3"),
    )
    client = TestClient(create_app(library_service=library_service))

    imported = client.post(
        "/v1/books/import",
        files={"file": ("integration.epub", build_epub(), "application/epub+zip")},
    )
    book_id = imported.json()["book"]["id"]
    chapter_id = imported.json()["chapters"][0]["id"]

    assert imported.status_code == 200
    assert client.get("/v1/books").json()["items"][0]["title"] == "Integration Book"
    assert client.get(f"/v1/books/{book_id}/chapters/{chapter_id}").json()["markdown"] == (
        "# Opening\n\nHello integration."
    )
```

- [ ] **Step 2: Run integration test**

Run:

```bash
uv run --extra dev pytest tests/api/test_library_integration.py -v
```

Expected: PASS.

- [ ] **Step 3: Update README**

Modify `README.md` with:

```markdown
## Import An Ebook

```bash
curl -X POST http://127.0.0.1:8000/v1/books/import \
  -F "file=@./book.epub"
```

Supported ebook formats in this phase:

- EPUB
- FB2
- FBZ

Imported source files and the SQLite library database are stored under `storage/`
by default. The storage and repository layers are isolated so deployments can
replace local files and SQLite in a future deployment.

## Library Endpoints

- `GET /v1/books`
- `GET /v1/books/{book_id}`
- `GET /v1/books/{book_id}/chapters`
- `GET /v1/books/{book_id}/chapters/{chapter_id}`
- `GET /v1/books/{book_id}/progress`
- `PUT /v1/books/{book_id}/progress`
- `POST /v1/books/{book_id}/bookmarks`
- `GET /v1/books/{book_id}/bookmarks`
- `DELETE /v1/books/{book_id}/bookmarks/{bookmark_id}`
```

- [ ] **Step 4: Run full test suite and linter**

Run:

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
git diff --check
```

Expected: PASS for all three commands.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md tests/api/test_library_integration.py
git commit -m "docs: document ebook library api"
```

- [ ] **Step 6: Request code review**

Use `superpowers:requesting-code-review` with:

- Description: Ebook library phase with EPUB/FB2/FBZ import, local storage, SQLite repository, service, API routes, progress, and bookmarks.
- Requirements: `docs/superpowers/specs/2026-05-20-ebook-library-design.md`
- Base SHA: commit before Task 1.
- Head SHA: current `HEAD`.

Fix Critical and Important findings before continuing.

- [ ] **Step 7: Final verification after review fixes**

Run fresh:

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
git status --short
```

Expected: tests and lint pass. `git status --short` should show only intentional
changes before any final commit, or be clean after the final commit.
