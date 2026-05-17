from io import BytesIO

from pypdf import PdfWriter

from free_for_read.core.models import DocumentNode
from free_for_read.parsers.pdf import PdfParser
from free_for_read.renderers.markdown import render_markdown


def test_pdf_parser_extracts_page_text_and_page_breaks() -> None:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "Tiny PDF"})
    writer.write(buffer)

    document = PdfParser().parse(
        buffer.getvalue(), source_url="https://example.com/tiny.pdf"
    )

    assert document.title == "Tiny PDF"
    assert render_markdown(document) == "---"


def test_pdf_parser_maps_extracted_text_to_page_metadata(monkeypatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        metadata = None
        pages = [FakePage("First paragraph\n\nSecond paragraph")]

        def __init__(self, content: BytesIO) -> None:
            assert content.getvalue() == b"%PDF fake"

    monkeypatch.setattr("free_for_read.parsers.pdf.PdfReader", FakeReader)

    document = PdfParser().parse(b"%PDF fake", source_url="https://example.com/text.pdf")

    assert document.root.children == [
        DocumentNode(
            type="paragraph",
            text="First paragraph",
            metadata={"page_number": 1},
        ),
        DocumentNode(
            type="paragraph",
            text="Second paragraph",
            metadata={"page_number": 1},
        ),
        DocumentNode(type="page_break", metadata={"page_number": 1}),
    ]
