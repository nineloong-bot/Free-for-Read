from free_for_read.core.models import SourceType
from free_for_read.detectors.content_type import detect_source_type


def test_detects_pdf_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/file",
        content_type="application/pdf",
        content=b"%PDF-1.7",
    ) == SourceType.PDF


def test_detects_pdf_from_content_sniffing() -> None:
    assert detect_source_type(
        url="https://example.com/file",
        content_type="application/octet-stream",
        content=b"%PDF-1.7",
    ) == SourceType.PDF


def test_detects_word_from_extension() -> None:
    assert detect_source_type(
        url="https://example.com/file.docx",
        content_type="application/octet-stream",
        content=b"PK\x03\x04",
    ) == SourceType.WORD


def test_detects_word_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/file",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        content=b"PK\x03\x04",
    ) == SourceType.WORD


def test_legacy_msword_mime_defaults_to_web() -> None:
    assert detect_source_type(
        url="https://example.com/file",
        content_type="application/msword",
        content=b"legacy doc bytes",
    ) == SourceType.WEB


def test_explicit_html_content_type_beats_misleading_docx_extension() -> None:
    assert detect_source_type(
        url="https://example.com/file.docx",
        content_type="text/html; charset=utf-8",
        content=b"<html><body>Article</body></html>",
    ) == SourceType.WEB


def test_html_sniffing_beats_misleading_pptx_extension() -> None:
    assert detect_source_type(
        url="https://example.com/slides.pptx",
        content_type="application/octet-stream",
        content=b"<!doctype html><html><body>Article</body></html>",
    ) == SourceType.WEB


def test_detects_powerpoint_from_extension() -> None:
    assert detect_source_type(
        url="https://example.com/slides.pptx",
        content_type="application/octet-stream",
        content=b"PK\x03\x04",
    ) == SourceType.POWERPOINT


def test_detects_powerpoint_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/slides",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
        content=b"PK\x03\x04",
    ) == SourceType.POWERPOINT


def test_detects_image_from_content_type() -> None:
    assert detect_source_type(
        url="https://example.com/image",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\n",
    ) == SourceType.IMAGE


def test_defaults_html_to_web() -> None:
    assert detect_source_type(
        url="https://example.com/article",
        content_type="text/html; charset=utf-8",
        content=b"<html><body>Article</body></html>",
    ) == SourceType.WEB


def test_detects_web_from_html_content_sniffing() -> None:
    assert detect_source_type(
        url="https://example.com/article",
        content_type="application/octet-stream",
        content=b"<!doctype html><html><body>Article</body></html>",
    ) == SourceType.WEB


def test_defaults_unknown_content_to_web() -> None:
    assert detect_source_type(
        url="https://example.com/download.bin",
        content_type="application/octet-stream",
        content=b"\x00\x01unknown",
    ) == SourceType.WEB
