from pathlib import PurePosixPath
from urllib.parse import urlparse

from free_for_read.core.models import SourceType


def detect_source_type(
    *,
    url: str,
    content_type: str | None,
    content: bytes,
) -> SourceType:
    normalized = (content_type or "").split(";")[0].strip().lower()
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    is_html = normalized in {"text/html", "application/xhtml+xml"} or (
        b"<html" in content[:512].lower()
    )

    if normalized == "application/pdf" or content.startswith(b"%PDF"):
        return SourceType.PDF
    if is_html:
        return SourceType.WEB
    if suffix == ".docx" or normalized in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return SourceType.WORD
    if suffix == ".pptx" or normalized in {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    }:
        return SourceType.POWERPOINT
    if normalized.startswith("image/"):
        return SourceType.IMAGE
    return SourceType.WEB
