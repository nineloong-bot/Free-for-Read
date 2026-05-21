# Phase 5: AI Reading Features Design

Date: 2026-05-21

## Goal

Add AI-powered reading: ask questions about the current book with source citations, and search across the entire library with semantic understanding. Uses a hybrid model strategy — cloud APIs by default, local Ollama optional.

## Strategy

All three AI components (LLM, Embeddings, Vector DB) follow the backend's existing interface-driven pattern:

- **LLM**: abstract protocol → OpenAI / Anthropic / Ollama implementations
- **Embeddings**: abstract protocol → sentence-transformers (local) / OpenAI (cloud) implementations
- **Vector DB**: ChromaDB, one collection per book

Configuration via environment variables (Phase 6 adds settings UI):

```
AI_PROVIDER=openai|anthropic|ollama (default: openai)
AI_API_KEY=<provider key>
AI_BASE_URL=<optional custom endpoint>
EMBED_PROVIDER=local|openai (default: local)
CHROMA_PATH=./storage/chroma (default)
```

## Architecture

```
Frontend (React)
  ├── AiPanel.tsx           — chat sidebar in ReaderView
  └── SearchBar.tsx         — semantic search in LibraryView
      │
Backend (Python / FastAPI)
  ├── free_for_read/ai/
  │   ├── chunking.py       — heading-aware Markdown splitter
  │   ├── embeddings.py     — embedding abstraction + providers
  │   ├── llm.py            — LLM abstraction + providers
  │   ├── rag.py            — RAG pipeline (retrieve → augment → generate)
  │   └── indexer.py        — book indexing into ChromaDB
  ├── free_for_read/api/
  │   ├── ai_routes.py      — POST /v1/books/{id}/chat + GET /v1/books/{id}/search
  │   └── ai_schemas.py     — request/response schemas
  └── ChromaDB              — persistent vector store
```

## Chunking Engine (`free_for_read/ai/chunking.py`)

Heading-aware Markdown splitter:

1. Parse chapter Markdown into heading + paragraph blocks.
2. Merge consecutive paragraphs into chunks targeting 512 tokens (~2000 chars Chinese).
3. Preserve heading context: each chunk carries its nearest heading as metadata.
4. Maximum chunk overlap of 50 tokens for continuity.
5. Each chunk stores: `text`, `book_id`, `chapter_id`, `chapter_title`, `heading_path` (e.g., "第十二章 > 红岸之三"), `chunk_index`.

```python
class Chunk(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    chapter_title: str
    heading_path: str
    text: str
    chunk_index: int
    token_count: int
```

Public API:

```python
def chunk_chapter(markdown: str, book_id: str, chapter_id: str, chapter_title: str, *, target_tokens: int = 512) -> list[Chunk]
```

## Embedding Abstraction (`free_for_read/ai/embeddings.py`)

Protocol pattern (same as existing parsers):

```python
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimension(self) -> int: ...
```

Two implementations:

- `LocalEmbeddingProvider`: wraps `sentence-transformers` with model `BAAI/bge-small-zh` (512-dim, ~100MB, Chinese-optimized). Lazy-loaded on first use.
- `OpenAIEmbeddingProvider`: wraps `text-embedding-3-small` (1536-dim). Requires `OPENAI_API_KEY`.

Factory:

```python
def create_embedding_provider(provider: str = "local", **kwargs) -> EmbeddingProvider
```

## LLM Abstraction (`free_for_read/ai/llm.py`)

```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class LlmProvider(Protocol):
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str: ...
```

Three implementations:

- `OpenAiLlmProvider`: OpenAI-compatible API (`/v1/chat/completions`). Works with OpenAI, DeepSeek, and any OpenAI-compatible endpoint including Ollama's OpenAI mode.
- `AnthropicLlmProvider`: Anthropic Messages API. Uses `claude-3-haiku` for cost efficiency as default, configurable.
- `OllamaLlmProvider`: Direct Ollama API for local models. Model default: `qwen2.5:7b`.

Configuration determines which provider is active at startup. No runtime switching for MVP.

## RAG Pipeline (`free_for_read/ai/rag.py`)

```python
class RagPipeline:
    def __init__(self, llm: LlmProvider, embeddings: EmbeddingProvider, chroma: chromadb.PersistentClient): ...

    async def query(self, book_id: str, question: str, *, top_k: int = 5) -> RagResponse:
        """Retrieve relevant chunks → augment → generate answer with citations"""

    def search(self, query: str, *, top_k: int = 10, book_id: str | None = None) -> list[SearchResult]:
        """Hybrid BM25 + vector search across library"""
```

### RagResponse

```json
{
  "answer": "叶文洁加入红岸工程是因为她的天体物理学背景...",
  "sources": [
    {
      "chapter_id": "chapter_abc",
      "chapter_title": "第十二章 红岸之三",
      "heading_path": "第十二章 > 红岸之三",
      "text": "...叶文洁被秘密调入红岸基地...",
      "relevance": 0.92
    }
  ],
  "model": "claude-3-haiku",
  "processing_ms": 1240
}
```

### Hybrid Search

BM25 (keyword) + vector similarity (semantic), weighted by `alpha` (default 0.7 for vector weight):

```
score = alpha * vector_score + (1 - alpha) * bm25_score
```

Implementation: `rank_bm25` for BM25, cosine similarity for vectors.

### System Prompt

```
你是一个阅读助手，帮助读者理解正在阅读的书籍内容。
你有这本书的全文知识，请基于提供的内容片段回答问题。
如果内容片段不足以回答，请诚实说明。
回答时引用具体的章节来源。
用中文回答。
```

## ChromaDB Integration

### Collection per book

Each imported book gets a ChromaDB collection named `book_{book_id}`. Indexing happens on import and on demand.

### Re-indexing

`POST /v1/books/{id}/reindex` — deletes existing collection, re-chunks all chapters, re-embeds.

### Storage

Stored under `storage/chroma/` alongside the SQLite database. Persisted across app restarts.

## API Design

### Chat

`POST /v1/books/{book_id}/chat`

Request:

```json
{
  "question": "叶文洁为什么加入红岸工程？",
  "chapter_id": "chapter_abc",  // optional, narrows context to current chapter
  "history": [                   // optional, conversation history
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response: `RagResponse`

Behavior:

1. Retrieve top_k=5 relevant chunks from ChromaDB (optionally scoped to `chapter_id`).
2. Build augmented prompt with retrieved chunks as context.
3. Call configured LLM.
4. Return answer + source citations.

### Search

`GET /v1/books/search?q=红岸基地&limit=10&book_id=book_xxx`

Response:

```json
{
  "results": [
    {
      "book_id": "book_xxx",
      "book_title": "三体",
      "chapter_id": "chapter_abc",
      "chapter_title": "第十二章 红岸之三",
      "text": "...刚进入红岸基地时...",
      "score": 0.92
    }
  ]
}
```

`book_id` is optional — omit to search all books.

### Reindex

`POST /v1/books/{book_id}/reindex`

Response: `{"status": "indexed", "chunk_count": 45}`

### Index Status

`GET /v1/books/{book_id}/index`

Response: `{"indexed": true, "chunk_count": 45, "last_indexed": "2026-05-21T..."}`

## Error Handling

Reuses the existing `ParseError` envelope. New error codes:

- `ai_provider_error` — LLM API call failed
- `embedding_error` — embedding generation failed
- `index_error` — ChromaDB operation failed
- `not_indexed` — book has no index (run reindex first)

## Frontend

### AiPanel Component

340px right sidebar in ReaderView. Toggle via a sparkle button in the ReaderToolbar.

States:

- **Empty**: welcome message with suggested questions
- **Loading**: "AI 正在思考..." with animated dots
- **Response**: answer text + expandable source citations
- **Error**: error message with retry button

Features:

- Input field + send button at bottom
- Conversation history (scrollable)
- Source citations with click-to-navigate to chapter

### SearchBar Component

In LibraryView header (visible when search icon clicked or always-on).

States:

- **Empty**: search input with placeholder
- **Loading**: inline spinner
- **Results**: result cards with book name, chapter, highlighted excerpt, relevance score
- **No results**: "未找到相关内容"

## Book Indexing

Auto-index on import: after `POST /v1/books/import` completes, trigger async indexing. Frontend polls `GET /v1/books/{id}/index` for status.

For Phase 5 MVP, indexing is synchronous but lightweight (single-chapter reindex is fast). Async jobs can be added later.

## Dependencies

- `chromadb>=0.5` — vector database
- `sentence-transformers>=3.0` — local embeddings
- `rank-bm25>=0.2` — BM25 keyword search
- `openai>=1.0` — OpenAI/OpenAI-compatible API client
- `anthropic>=0.30` — Anthropic API client

All optional at import time — only the configured provider's dependency is required at runtime.

## Out of Scope

- TTS (deferred)
- Reading statistics (Phase 6)
- Settings UI for AI configuration (Phase 6 — env vars for MVP)
- Multi-turn conversation memory beyond session
- Book summarization (separate feature)
- Custom AI skills system (ReadAny feature, not planned)

## Acceptance Criteria

- Imported books are auto-indexed into ChromaDB.
- `POST /v1/books/{id}/chat` returns grounded answers with source citations.
- `GET /v1/books/search?q=...` returns ranked results across all books.
- Chat works with OpenAI, Anthropic, and Ollama (configurable).
- Embeddings work with both local bge-small-zh and OpenAI.
- AiPanel appears in ReaderView and supports question-answer flow.
- SearchBar provides semantic search in LibraryView.
- All existing Phase 1-4 tests still pass.
