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
    assert parsed.word_count == 8


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


def test_parse_epub_wraps_unsafe_container_xml() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
            <!DOCTYPE container [
              <!ENTITY unsafe "OPS/package.opf">
            ]>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles><rootfile full-path="&unsafe;"/></rootfiles>
            </container>""",
        )

    with pytest.raises(ParseError) as exc_info:
        parse_epub(buffer.getvalue(), filename="unsafe.epub")

    assert exc_info.value.code == "invalid_ebook"
