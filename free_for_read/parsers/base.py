from typing import Protocol

from free_for_read.core.models import Document, SourceType


class Parser(Protocol):
    source_type: SourceType

    def parse(self, content: bytes, *, source_url: str) -> Document:
        raise NotImplementedError
