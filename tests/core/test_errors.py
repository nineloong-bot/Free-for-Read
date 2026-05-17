import pytest

from free_for_read.core.errors import ParseError


def test_parse_error_serializes_code_message_and_details() -> None:
    error = ParseError(
        code="fetch_failed",
        message="Unable to fetch URL.",
        details={"url": "https://example.com"},
    )

    assert error.to_dict() == {
        "code": "fetch_failed",
        "message": "Unable to fetch URL.",
        "details": {"url": "https://example.com"},
    }


def test_parse_error_defaults_details_to_empty_dict() -> None:
    error = ParseError(code="fetch_failed", message="Unable to fetch URL.")

    assert error.details == {}
    assert error.to_dict() == {
        "code": "fetch_failed",
        "message": "Unable to fetch URL.",
        "details": {},
    }


def test_parse_error_stores_attributes_and_exception_message() -> None:
    error = ParseError(
        code="fetch_timeout",
        message="Timed out while fetching source URL.",
        details={"url": "https://example.com/slow"},
    )

    assert error.code == "fetch_timeout"
    assert error.message == "Timed out while fetching source URL."
    assert error.details == {"url": "https://example.com/slow"}
    assert str(error) == "Timed out while fetching source URL."


def test_parse_error_requires_keyword_arguments() -> None:
    with pytest.raises(TypeError):
        ParseError("fetch_failed", "Unable to fetch URL.")  # type: ignore[misc]
