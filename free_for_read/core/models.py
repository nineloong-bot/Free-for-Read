from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    WEB = "web"
    PDF = "pdf"
    WORD = "word"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    EPUB = "epub"
    FB2 = "fb2"
    FBZ = "fbz"


NodeType = Literal[
    "document",
    "heading",
    "paragraph",
    "list",
    "list_item",
    "table",
    "table_row",
    "table_cell",
    "image",
    "page_break",
    "slide",
]


class DocumentNode(BaseModel):
    type: NodeType
    text: str | None = None
    level: int | None = None
    children: list["DocumentNode"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    root: DocumentNode
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseMetadata(BaseModel):
    title: str | None = None
    source_url: str
    source_type: SourceType
    word_count: int
    processing_ms: int
    content_length: int | None = None
