import pytest

from free_for_read.core.errors import ParseError
from free_for_read.core.models import SourceType
from free_for_read.parsers.registry import default_parser_registry


def test_default_registry_returns_parsers_for_supported_source_types() -> None:
    registry = default_parser_registry()

    assert registry.get(SourceType.WEB).source_type == SourceType.WEB
    assert registry.get(SourceType.PDF).source_type == SourceType.PDF
    assert registry.get(SourceType.WORD).source_type == SourceType.WORD
    assert registry.get(SourceType.POWERPOINT).source_type == SourceType.POWERPOINT


def test_default_registry_returns_parser_for_image() -> None:
    registry = default_parser_registry(include_images=True)

    parser = registry.get(SourceType.IMAGE)

    assert parser.source_type == SourceType.IMAGE


def test_registry_raises_for_unregistered_source_type() -> None:
    registry = default_parser_registry(include_images=False)

    with pytest.raises(ParseError) as exc_info:
        registry.get(SourceType.IMAGE)

    assert exc_info.value.code == "unsupported_source_type"
    assert exc_info.value.details["source_type"] == SourceType.IMAGE.value
