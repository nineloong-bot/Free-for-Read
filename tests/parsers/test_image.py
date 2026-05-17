import pytest

from free_for_read.core.errors import ParseError
from free_for_read.parsers.image import ImageParser


def test_image_parser_reports_unsupported_source_type() -> None:
    with pytest.raises(ParseError) as exc_info:
        ImageParser().parse(b"image-bytes", source_url="https://example.com/image.png")

    assert exc_info.value.code == "unsupported_source_type"
    assert exc_info.value.details["source_url"] == "https://example.com/image.png"
    assert exc_info.value.details["source_type"] == "image"
