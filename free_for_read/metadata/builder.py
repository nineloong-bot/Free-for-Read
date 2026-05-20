import re

from free_for_read.core.models import Document, ParseMetadata, SourceType

WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def count_words(markdown: str) -> int:
    return len(WORD_RE.findall(markdown))


def build_metadata(
    *,
    document: Document,
    markdown: str,
    source_url: str,
    source_type: SourceType,
    processing_ms: int,
    content_length: int | None,
) -> ParseMetadata:
    return ParseMetadata(
        title=document.title,
        source_url=source_url,
        source_type=source_type,
        word_count=count_words(markdown),
        processing_ms=processing_ms,
        content_length=content_length,
    )
