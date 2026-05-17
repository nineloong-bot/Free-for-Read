from free_for_read.core.errors import ParseError
from free_for_read.core.models import SourceType
from free_for_read.parsers.base import Parser
from free_for_read.parsers.image import ImageParser
from free_for_read.parsers.office import PowerPointParser, WordParser
from free_for_read.parsers.pdf import PdfParser
from free_for_read.parsers.web import WebParser


class ParserRegistry:
    def __init__(self, parsers: list[Parser]) -> None:
        self._parsers = {parser.source_type: parser for parser in parsers}

    def get(self, source_type: SourceType) -> Parser:
        parser = self._parsers.get(source_type)
        if parser is None:
            raise ParseError(
                code="unsupported_source_type",
                message=f"Unsupported source type: {source_type.value}.",
                details={"source_type": source_type.value},
            )
        return parser


def default_parser_registry(*, include_images: bool = True) -> ParserRegistry:
    parsers: list[Parser] = [
        WebParser(),
        PdfParser(),
        WordParser(),
        PowerPointParser(),
    ]
    if include_images:
        parsers.append(ImageParser())
    return ParserRegistry(parsers)
