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


def build_epub() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
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
                <dc:title>Sample EPUB</dc:title>
              </metadata>
              <manifest>
                <item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/>
              </manifest>
              <spine>
                <itemref idref="c1"/>
              </spine>
            </package>""",
        )
        archive.writestr(
            "OPS/chapter.xhtml",
            "<html><body><h1>EPUB Chapter</h1><p>Hello EPUB.</p></body></html>",
        )
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


def test_parse_fbz_uses_safe_entry_when_unsafe_entry_appears_first() -> None:
    unsafe = FB2_TEXT.replace("Sample FB2", "Unsafe FB2")
    safe = FB2_TEXT.replace("Sample FB2", "Safe FB2")
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../evil.fb2", unsafe.encode("utf-8"))
        archive.writestr("safe.fb2", safe.encode("utf-8"))

    parsed = parse_fbz(buffer.getvalue(), filename="sample.fbz")

    assert parsed.title == "Safe FB2"


def test_parse_fbz_rejects_archive_with_only_unsafe_fb2_entries() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../evil.fb2", FB2_TEXT.encode("utf-8"))

    with pytest.raises(ParseError) as exc_info:
        parse_fbz(buffer.getvalue(), filename="unsafe.fbz")

    assert exc_info.value.code == "invalid_ebook"


def test_parse_ebook_dispatches_fb2_by_filename() -> None:
    parsed = parse_ebook(FB2_TEXT.encode("utf-8"), filename="sample.fb2")

    assert parsed.source_type == EbookSourceType.FB2


def test_parse_ebook_dispatches_epub_by_filename() -> None:
    parsed = parse_ebook(build_epub(), filename="sample.epub")

    assert parsed.source_type == EbookSourceType.EPUB
    assert parsed.title == "Sample EPUB"
    assert parsed.chapters[0].title == "EPUB Chapter"


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


def test_parse_fb2_wraps_unsafe_xml() -> None:
    content = b"""<?xml version="1.0"?>
    <!DOCTYPE FictionBook [
      <!ENTITY unsafe "Sample FB2">
    ]>
    <FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
      <description><title-info><book-title>&unsafe;</book-title></title-info></description>
      <body><section><p>Hello reader.</p></section></body>
    </FictionBook>"""

    with pytest.raises(ParseError) as exc_info:
        parse_fb2(content, filename="unsafe.fb2")

    assert exc_info.value.code == "invalid_ebook"


def test_parse_fb2_rejects_namespace_less_document_as_invalid_ebook() -> None:
    content = FB2_TEXT.replace(' xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"', "")

    with pytest.raises(ParseError) as exc_info:
        parse_fb2(content.encode("utf-8"), filename="namespace-less.fb2")

    assert exc_info.value.code == "invalid_ebook"


def test_parse_fb2_collects_readable_nested_sections_in_document_order() -> None:
    content = """<?xml version="1.0" encoding="utf-8"?>
    <FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
      <description>
        <title-info>
          <book-title>Nested FB2</book-title>
        </title-info>
      </description>
      <body>
        <section>
          <title><p>Part</p></title>
          <section>
            <title><p>Nested One</p></title>
            <p>First nested paragraph.</p>
          </section>
          <section>
            <title><p>Nested Two</p></title>
            <p>Second nested paragraph.</p>
          </section>
        </section>
      </body>
    </FictionBook>
    """

    parsed = parse_fb2(content.encode("utf-8"), filename="nested.fb2")

    assert [chapter.title for chapter in parsed.chapters] == ["Nested One", "Nested Two"]
    assert parsed.chapters[0].markdown == "# Nested One\n\nFirst nested paragraph."
    assert parsed.chapters[0].source_ref == "body/section[1]/section[1]"
    assert parsed.chapters[1].source_ref == "body/section[1]/section[2]"
