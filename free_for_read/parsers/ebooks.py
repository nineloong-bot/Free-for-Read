from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from bs4 import BeautifulSoup
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

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
    except (BadZipFile, DefusedXmlException, ElementTree.ParseError, KeyError) as exc:
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
        if not root.tag.startswith("{"):
            raise ParseError(
                code="invalid_ebook",
                message="FB2 document must declare the FictionBook namespace.",
                details={"filename": filename},
            )
        ns = {"fb2": root.tag.split("}", 1)[0].strip("{")}
        title = _fb2_text(root, ".//fb2:book-title", ns) or _fallback_title(filename)
        language = _fb2_text(root, ".//fb2:lang", ns)
        author = _fb2_author(root, ns)
        chapters = _fb2_chapters(root, ns)
    except ParseError:
        raise
    except (DefusedXmlException, ElementTree.ParseError) as exc:
        raise ParseError(
            code="invalid_ebook",
            message="Invalid FB2 file.",
            details={"filename": filename},
        ) from exc
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
                name
                for name in archive.namelist()
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
    chapters: list[ParsedChapter] = []
    bodies = [
        body for body in root.findall("./fb2:body", ns) if body.attrib.get("name") is None
    ]
    for body in bodies:
        for position, section in enumerate(body.findall("fb2:section", ns), start=1):
            _collect_fb2_sections(section, ns, f"body/section[{position}]", chapters)
    if not chapters:
        raise ParseError(code="invalid_ebook", message="FB2 contains no readable chapters.")
    return chapters


def _collect_fb2_sections(
    section: ElementTree.Element,
    ns: dict[str, str],
    source_ref: str,
    chapters: list[ParsedChapter],
) -> None:
    title = _fb2_text(section, "fb2:title", ns) or f"Chapter {len(chapters) + 1}"
    paragraphs = [_fb2_text(paragraph, ".", ns) for paragraph in section.findall("fb2:p", ns)]
    body = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    if body:
        markdown = f"# {title}\n\n{body}"
        chapters.append(
            ParsedChapter(
                index=len(chapters),
                title=title,
                markdown=markdown,
                word_count=count_words(markdown),
                source_ref=source_ref,
            )
        )
    for position, child in enumerate(section.findall("fb2:section", ns), start=1):
        _collect_fb2_sections(child, ns, f"{source_ref}/section[{position}]", chapters)


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
