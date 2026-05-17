from free_for_read.core.errors import ParseError
from free_for_read.core.models import Document, SourceType


class ImageParser:
    source_type = SourceType.IMAGE

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise ParseError(
            code="unsupported_source_type",
            message="Image parsing requires OCR support, which is not enabled in this version.",
            details={"source_url": source_url, "source_type": self.source_type.value},
        )
