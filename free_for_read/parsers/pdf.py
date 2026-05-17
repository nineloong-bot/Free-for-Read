from io import BytesIO

from pypdf import PdfReader

from free_for_read.core.models import Document, DocumentNode, SourceType


class PdfParser:
    source_type = SourceType.PDF

    def parse(self, content: bytes, *, source_url: str) -> Document:
        reader = PdfReader(BytesIO(content))
        root = DocumentNode(type="document")
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for paragraph in _paragraphs(text):
                root.children.append(
                    DocumentNode(
                        type="paragraph",
                        text=paragraph,
                        metadata={"page_number": index},
                    )
                )
            root.children.append(
                DocumentNode(type="page_break", metadata={"page_number": index})
            )
        return Document(root=root, title=_title(reader))


def _paragraphs(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _title(reader: PdfReader) -> str | None:
    metadata = reader.metadata
    if metadata and metadata.title:
        return str(metadata.title)
    return None
