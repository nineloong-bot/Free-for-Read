from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str
    chapter_id: str | None = None
    history: list[dict] = Field(default_factory=list)


class SourceItem(BaseModel):
    chapter_id: str
    chapter_title: str
    heading_path: str
    text: str
    relevance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    model: str
    processing_ms: int


class SearchResultItem(BaseModel):
    book_id: str
    book_title: str
    chapter_id: str
    chapter_title: str
    text: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]


class ReindexResponse(BaseModel):
    status: str
    chunk_count: int


class IndexStatusResponse(BaseModel):
    indexed: bool
    chunk_count: int | None = None
    last_indexed: str | None = None
