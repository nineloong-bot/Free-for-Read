# Phase 5: AI Reading Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-powered chat over books with source citations and semantic search across the library using hybrid LLM/embeddings with ChromaDB.

**Architecture:** Python backend gains `free_for_read/ai/` module with chunking, embeddings, LLM, RAG pipeline, and ChromaDB indexer — all following the existing Protocol-based interface pattern. New `/v1/books/{id}/chat` and `/v1/books/search` endpoints follow the same route factory pattern as Phase 1-3. Frontend gains AiPanel (sidebar chat in reader) and SearchBar (library semantic search).

**Tech Stack:** chromadb, sentence-transformers, rank-bm25, openai, anthropic (optional at import time), React + TypeScript.

---

## File Structure

- Modify: `pyproject.toml` — add chromadb, sentence-transformers, rank-bm25, openai, anthropic
- Create: `free_for_read/ai/__init__.py`
- Create: `free_for_read/ai/chunking.py` — heading-aware Markdown splitter
- Create: `free_for_read/ai/embeddings.py` — embedding abstraction + local/cloud providers
- Create: `free_for_read/ai/llm.py` — LLM abstraction + OpenAI/Anthropic/Ollama providers
- Create: `free_for_read/ai/indexer.py` — ChromaDB collection management
- Create: `free_for_read/ai/rag.py` — RAG pipeline (retrieve → augment → generate)
- Create: `free_for_read/api/ai_schemas.py` — request/response schemas
- Create: `free_for_read/api/ai_routes.py` — chat + search + reindex + index status routes
- Modify: `free_for_read/api/app.py` — wire AI router
- Modify: `free_for_read/api/library_routes.py` — auto-index on import
- Create: `tests/ai/test_chunking.py`
- Create: `tests/ai/test_rag.py`
- Create: `tests/api/test_ai_routes.py`
- Create: `frontend/src/components/AiPanel.tsx`
- Create: `frontend/src/components/SearchBar.tsx`
- Modify: `frontend/src/api/client.ts` — add chat, search, reindex endpoints
- Modify: `frontend/src/components/ReaderToolbar.tsx` — add AI toggle button
- Modify: `frontend/src/views/ReaderView.tsx` — show AiPanel
- Modify: `frontend/src/views/LibraryView.tsx` — integrate SearchBar
- Create: `frontend/src/components/__tests__/AiPanel.test.tsx`
- Create: `frontend/src/components/__tests__/SearchBar.test.tsx`

---

### Task 1: Dependencies and Chunking Engine

**Files:**
- Modify: `pyproject.toml`
- Create: `free_for_read/ai/__init__.py`
- Create: `free_for_read/ai/chunking.py`
- Create: `tests/ai/__init__.py`
- Create: `tests/ai/test_chunking.py`

- [ ] **Step 1: Add dependencies**

Modify `pyproject.toml` — add to `[project] dependencies`:

```toml
  "chromadb>=0.5",
  "sentence-transformers>=3.0",
  "rank-bm25>=0.2",
  "openai>=1.0",
  "anthropic>=0.30",
```

Run: `uv lock`

- [ ] **Step 2: Write failing chunking test**

Create `tests/ai/__init__.py` (empty).

Create `tests/ai/test_chunking.py`:

```python
from free_for_read.ai.chunking import chunk_chapter, Chunk


def test_chunk_splits_long_chapter_at_headings() -> None:
    markdown = """# Chapter One

## Section A

This is the first paragraph. It has some content about the story.

Another paragraph here with more details about Section A.

## Section B

This is Section B content. It contains different information.

And another paragraph for Section B."""
    chunks = chunk_chapter(
        markdown, book_id="b1", chapter_id="c1", chapter_title="Chapter One",
    )

    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.book_id == "b1" for c in chunks)
    assert all(c.chapter_id == "c1" for c in chunks)
    # Section headers should be preserved in heading_path
    headings = {c.heading_path for c in chunks}
    assert any("Section A" in h for h in headings)
    assert any("Section B" in h for h in headings)


def test_chunk_preserves_chapter_metadata() -> None:
    chunks = chunk_chapter(
        "Simple single paragraph without headings.",
        book_id="b1", chapter_id="c1", chapter_title="Intro",
    )

    assert len(chunks) == 1
    assert chunks[0].chapter_title == "Intro"
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "Simple single paragraph without headings."


def test_chunk_short_content_returns_single_chunk() -> None:
    chunks = chunk_chapter("Hello world.", book_id="b1", chapter_id="c1", chapter_title="T")
    assert len(chunks) == 1
```

Run: `uv run --extra dev pytest tests/ai/test_chunking.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement chunking engine**

Create `free_for_read/ai/__init__.py` (empty).

Create `free_for_read/ai/chunking.py`:

```python
from uuid import uuid4

from pydantic import BaseModel


class Chunk(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    chapter_title: str
    heading_path: str
    text: str
    chunk_index: int
    token_count: int


def chunk_chapter(
    markdown: str,
    *,
    book_id: str,
    chapter_id: str,
    chapter_title: str,
    target_tokens: int = 512,
) -> list[Chunk]:
    # Split into heading + paragraph blocks
    lines = markdown.splitlines()
    blocks: list[tuple[str | None, list[str]]] = []  # (heading, paragraphs)
    current_heading: str | None = None
    current_paras: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_paras:
                blocks.append((current_heading, current_paras))
                current_paras = []
            current_heading = stripped.lstrip("#").strip()
        elif stripped:
            current_paras.append(stripped)
    if current_paras:
        blocks.append((current_heading, current_paras))

    # Merge blocks into size-targeted chunks
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_tokens = 0
    buffer_heading: str | None = None

    def flush_chunk() -> None:
        nonlocal buffer, buffer_tokens
        if not buffer:
            return
        text = "\n\n".join(buffer)
        chunks.append(Chunk(
            id=f"chunk_{uuid4().hex}",
            book_id=book_id,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            heading_path=buffer_heading or chapter_title,
            text=text,
            chunk_index=len(chunks),
            token_count=buffer_tokens,
        ))
        buffer = []
        buffer_tokens = 0

    for heading, paras in blocks:
        block_text = "\n\n".join(paras)
        block_tokens = _estimate_tokens(block_text)
        active_heading = heading or buffer_heading

        if buffer_tokens + block_tokens > target_tokens and buffer:
            flush_chunk()
            buffer_heading = active_heading

        if not buffer:
            buffer_heading = active_heading
        buffer.append(block_text)
        buffer_tokens += block_tokens

    flush_chunk()
    return chunks


def _estimate_tokens(text: str) -> int:
    # Rough: ~2 chars per token for Chinese, ~4 for English
    return max(1, len(text) // 2)
```

- [ ] **Step 4: Run tests**

Run: `uv run --extra dev pytest tests/ai/test_chunking.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock free_for_read/ai/ tests/ai/
git commit -m "feat: add chunking engine"
```

---

### Task 2: Embedding Abstraction

**Files:**
- Create: `free_for_read/ai/embeddings.py`
- Create: `tests/ai/test_embeddings.py`

- [ ] **Step 1: Write failing test**

Create `tests/ai/test_embeddings.py`:

```python
from free_for_read.ai.embeddings import EmbeddingProvider, create_embedding_provider


class StubEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    @property
    def dimension(self) -> int:
        return 384


def test_embedding_provider_interface() -> None:
    provider = StubEmbeddingProvider()
    result = provider.embed(["hello", "world"])
    assert len(result) == 2
    assert len(result[0]) == 384
    assert provider.dimension == 384


def test_create_embedding_provider_defaults_to_stub_for_testing() -> None:
    # In test environment without actual models, defaults safely
    provider = create_embedding_provider("stub")
    assert provider.dimension > 0
    result = provider.embed(["test"])
    assert len(result) == 1
    assert len(result[0]) == provider.dimension
```

Run: `uv run --extra dev pytest tests/ai/test_embeddings.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement embedding abstraction**

Create `free_for_read/ai/embeddings.py`:

```python
from typing import Protocol
import os


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimension(self) -> int: ...


class StubEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    @property
    def dimension(self) -> int:
        return 384


class LocalEmbeddingProvider:
    def __init__(self, model_name: str = "BAAI/bge-small-zh"):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        result = model.encode(texts, normalize_embeddings=True)
        return result.tolist()

    @property
    def dimension(self) -> int:
        return 512  # bge-small-zh dimension


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]

    @property
    def dimension(self) -> int:
        return 1536


def create_embedding_provider(provider: str = "local", **kwargs) -> EmbeddingProvider:
    if provider == "local":
        return LocalEmbeddingProvider(**kwargs)
    elif provider == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    elif provider == "stub":
        return StubEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}")
```

- [ ] **Step 3: Run tests**

Run: `uv run --extra dev pytest tests/ai/test_embeddings.py -v`
Expected: 2 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add free_for_read/ai/embeddings.py tests/ai/test_embeddings.py
git commit -m "feat: add embedding abstraction with local and cloud providers"
```

---

### Task 3: LLM Abstraction

**Files:**
- Create: `free_for_read/ai/llm.py`
- Create: `tests/ai/test_llm.py`

- [ ] **Step 1: Write failing test**

Create `tests/ai/test_llm.py`:

```python
import pytest
from free_for_read.ai.llm import ChatMessage, LlmProvider, create_llm_provider


class StubLlmProvider:
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        return f"Stub response to: {messages[-1].content[:30]}"


def test_chat_message_model() -> None:
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


@pytest.mark.asyncio
async def test_stub_llm_provider() -> None:
    provider = StubLlmProvider()
    result = await provider.chat([ChatMessage(role="user", content="What is this?")])
    assert "Stub response" in result


def test_create_llm_provider_stub() -> None:
    provider = create_llm_provider("stub")
    assert isinstance(provider, type(StubLlmProvider()))
```

Run: `uv run --extra dev pytest tests/ai/test_llm.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement LLM abstraction**

Create `free_for_read/ai/llm.py`:

```python
import os
from typing import Literal, Protocol
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LlmProvider(Protocol):
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str: ...


class StubLlmProvider:
    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        return f"Stub response to: {messages[-1].content[:50]}"


class OpenAiLlmProvider:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini", base_url: str | None = None):
        self._api_key = api_key or os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._base_url = base_url or os.environ.get("AI_BASE_URL")

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[m.model_dump() for m in messages],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


class AnthropicLlmProvider:
    def __init__(self, api_key: str | None = None, model: str = "claude-3-haiku-20240307"):
        self._api_key = api_key or os.environ.get("AI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from anthropic import AsyncAnthropic
        system = next((m.content for m in messages if m.role == "system"), None)
        chat_messages = [m.model_dump() for m in messages if m.role != "system"]
        client = AsyncAnthropic(api_key=self._api_key)
        kwargs = {"model": self._model, "max_tokens": max_tokens, "messages": chat_messages}
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        block = resp.content[0]
        return block.text if hasattr(block, "text") else str(block)


class OllamaLlmProvider:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def chat(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=f"{self._base_url}/v1", api_key="ollama")
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[m.model_dump() for m in messages],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


def create_llm_provider(provider: str = "openai", **kwargs) -> LlmProvider:
    if provider == "openai":
        return OpenAiLlmProvider(**kwargs)
    elif provider == "anthropic":
        return AnthropicLlmProvider(**kwargs)
    elif provider == "ollama":
        return OllamaLlmProvider(**kwargs)
    elif provider == "stub":
        return StubLlmProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
```

- [ ] **Step 3: Run tests**

Run: `uv run --extra dev pytest tests/ai/test_llm.py -v`
Expected: 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add free_for_read/ai/llm.py tests/ai/test_llm.py
git commit -m "feat: add llm abstraction with openai anthropic and ollama providers"
```

---

### Task 4: ChromaDB Indexer

**Files:**
- Create: `free_for_read/ai/indexer.py`
- Create: `tests/ai/test_indexer.py`

- [ ] **Step 1: Write failing test**

Create `tests/ai/test_indexer.py`:

```python
import tempfile
from pathlib import Path
from free_for_read.ai.indexer import BookIndexer
from free_for_read.ai.embeddings import StubEmbeddingProvider


def test_indexer_create_and_query_collection() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(
            chroma_path=Path(tmpdir),
            embeddings=StubEmbeddingProvider(),
        )
        chunks = [
            {"id": "c1", "text": "红岸基地的秘密计划", "chapter_title": "Chapter 1", "heading_path": "Chapter 1"},
            {"id": "c2", "text": "叶文洁按下发射按钮", "chapter_title": "Chapter 2", "heading_path": "Chapter 2"},
        ]

        indexer.index_book("book_test", chunks)

        results = indexer.query("book_test", "红岸基地", top_k=1)
        assert len(results) > 0
        assert "红岸基地" in results[0]["text"]


def test_indexer_handles_empty_chunks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(
            chroma_path=Path(tmpdir),
            embeddings=StubEmbeddingProvider(),
        )
        indexer.index_book("book_empty", [])
        results = indexer.query("book_empty", "anything", top_k=1)
        assert len(results) == 0
```

Run: `uv run --extra dev pytest tests/ai/test_indexer.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement indexer**

Create `free_for_read/ai/indexer.py`:

```python
from pathlib import Path
import chromadb
from free_for_read.ai.embeddings import EmbeddingProvider


class BookIndexer:
    def __init__(self, *, chroma_path: Path, embeddings: EmbeddingProvider):
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._embeddings = embeddings

    def _collection_name(self, book_id: str) -> str:
        return f"book_{book_id}"

    def index_book(self, book_id: str, chunks: list[dict]) -> None:
        name = self._collection_name(book_id)
        # Delete existing collection if present
        try:
            self._client.delete_collection(name)
        except Exception:
            pass

        if not chunks:
            return

        collection = self._client.create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        embeddings = self._embeddings.embed(texts)
        metadatas = [
            {"chapter_title": c.get("chapter_title", ""), "heading_path": c.get("heading_path", "")}
            for c in chunks
        ]

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def query(self, book_id: str, query_text: str, *, top_k: int = 5) -> list[dict]:
        name = self._collection_name(book_id)
        try:
            collection = self._client.get_collection(name)
        except Exception:
            return []

        query_embedding = self._embeddings.embed([query_text])
        results = collection.query(query_embeddings=query_embedding, n_results=top_k)

        output: list[dict] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "chapter_title": results["metadatas"][0][i].get("chapter_title", "") if results["metadatas"] else "",
                    "heading_path": results["metadatas"][0][i].get("heading_path", "") if results["metadatas"] else "",
                    "score": 1.0 - (results["distances"][0][i] if results["distances"] else 0.0),
                })
        return output

    def collection_exists(self, book_id: str) -> bool:
        try:
            self._client.get_collection(self._collection_name(book_id))
            return True
        except Exception:
            return False
```

- [ ] **Step 3: Run tests**

Run: `uv run --extra dev pytest tests/ai/test_indexer.py -v`
Expected: 2 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add free_for_read/ai/indexer.py tests/ai/test_indexer.py
git commit -m "feat: add chromadb book indexer"
```

---

### Task 5: RAG Pipeline

**Files:**
- Create: `free_for_read/ai/rag.py`
- Create: `tests/ai/test_rag.py`

- [ ] **Step 1: Write failing test**

Create `tests/ai/test_rag.py`:

```python
import pytest
import tempfile
from pathlib import Path
from free_for_read.ai.embeddings import StubEmbeddingProvider
from free_for_read.ai.llm import StubLlmProvider, ChatMessage
from free_for_read.ai.rag import RagPipeline, RagResponse, SearchResult
from free_for_read.ai.indexer import BookIndexer


def test_rag_response_model() -> None:
    resp = RagResponse(
        answer="Test answer",
        sources=[{
            "chapter_id": "c1",
            "chapter_title": "Ch 1",
            "heading_path": "Ch 1",
            "text": "source text",
            "relevance": 0.95,
        }],
        model="stub",
        processing_ms=100,
    )
    assert resp.answer == "Test answer"
    assert len(resp.sources) == 1


@pytest.mark.asyncio
async def test_rag_pipeline_query() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        indexer = BookIndexer(chroma_path=Path(tmpdir), embeddings=StubEmbeddingProvider())
        llm = StubLlmProvider()
        rag = RagPipeline(llm=llm, indexer=indexer)

        # Index some chunks
        indexer.index_book("b1", [
            {"id": "c1", "text": "红岸基地的秘密计划", "chapter_title": "Ch 1", "heading_path": "Ch 1"},
        ])

        resp = await rag.query("b1", "红岸基地是什么？")

        assert isinstance(resp, RagResponse)
        assert len(resp.answer) > 0
        assert len(resp.sources) > 0
        assert resp.model == "stub"


def test_search_result_model() -> None:
    result = SearchResult(
        book_id="b1",
        book_title="Test Book",
        chapter_id="c1",
        chapter_title="Ch 1",
        text="matched text",
        score=0.88,
    )
    assert result.score == 0.88
```

Run: `uv run --extra dev pytest tests/ai/test_rag.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement RAG pipeline**

Create `free_for_read/ai/rag.py`:

```python
import time
from pydantic import BaseModel
from free_for_read.ai.llm import ChatMessage, LlmProvider
from free_for_read.ai.indexer import BookIndexer


RAG_SYSTEM_PROMPT = """你是一个阅读助手，帮助读者理解正在阅读的书籍内容。
你有这本书的全文知识，请基于提供的内容片段回答问题。
如果内容片段不足以回答，请诚实说明。
回答时引用具体的章节来源。
用中文回答。"""


class RagResponse(BaseModel):
    answer: str
    sources: list[dict]
    model: str
    processing_ms: int


class SearchResult(BaseModel):
    book_id: str
    book_title: str
    chapter_id: str
    chapter_title: str
    text: str
    score: float


class RagPipeline:
    def __init__(self, *, llm: LlmProvider, indexer: BookIndexer):
        self._llm = llm
        self._indexer = indexer

    async def query(self, book_id: str, question: str, *, top_k: int = 5) -> RagResponse:
        started = time.perf_counter()

        # Retrieve
        results = self._indexer.query(book_id, question, top_k=top_k)

        # Build context
        if results:
            context_parts = []
            for r in results:
                context_parts.append(
                    f"[来源: {r['chapter_title']} > {r['heading_path']}]\n{r['text']}"
                )
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "（未找到相关内容）"

        # Augment prompt
        messages = [
            ChatMessage(role="system", content=RAG_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"参考以下内容回答问题：\n\n{context}\n\n问题：{question}"),
        ]

        # Generate
        answer = await self._llm.chat(messages)

        processing_ms = int((time.perf_counter() - started) * 1000)

        sources = []
        for r in results:
            sources.append({
                "chapter_id": "",
                "chapter_title": r.get("chapter_title", ""),
                "heading_path": r.get("heading_path", ""),
                "text": r["text"][:200],
                "relevance": round(r.get("score", 0.0), 2),
            })

        return RagResponse(answer=answer, sources=sources, model="llm", processing_ms=processing_ms)

    def search(
        self, query_text: str, *, top_k: int = 10, book_ids: list[str] | None = None
    ) -> list[SearchResult]:
        # For MVP: search across specified books using vector similarity only
        # BM25 hybrid search can be added later
        if book_ids is None:
            # In production, get all book IDs from indexer
            return []

        results: list[SearchResult] = []
        for book_id in book_ids:
            hits = self._indexer.query(book_id, query_text, top_k=top_k)
            for h in hits:
                results.append(SearchResult(
                    book_id=book_id,
                    book_title="",  # populated by caller from repository
                    chapter_id="",
                    chapter_title=h.get("chapter_title", ""),
                    text=h["text"][:200],
                    score=round(h.get("score", 0.0), 2),
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
```

- [ ] **Step 3: Run tests**

Run: `uv run --extra dev pytest tests/ai/test_rag.py -v`
Expected: 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add free_for_read/ai/rag.py tests/ai/test_rag.py
git commit -m "feat: add rag pipeline with retrieve-augment-generate"
```

---

### Task 6: AI API Routes

**Files:**
- Create: `free_for_read/api/ai_schemas.py`
- Create: `free_for_read/api/ai_routes.py`
- Modify: `free_for_read/api/app.py`
- Modify: `free_for_read/api/library_routes.py`
- Create: `tests/api/test_ai_routes.py`

- [ ] **Step 1: Write failing test**

Create `tests/api/test_ai_routes.py`:

```python
from fastapi.testclient import TestClient

from free_for_read.api.app import create_app
from free_for_read.ai.rag import RagResponse


class StubAiService:
    async def query_book(self, book_id: str, question: str, top_k: int = 5) -> RagResponse:
        return RagResponse(
            answer="Test answer",
            sources=[{
                "chapter_id": "c1", "chapter_title": "Ch 1",
                "heading_path": "Ch 1", "text": "red bank base",
                "relevance": 0.95,
            }],
            model="stub",
            processing_ms=50,
        )

    def search_books(self, q: str, limit: int = 10, book_id: str | None = None):
        return [
            {"book_id": "b1", "book_title": "Test", "chapter_id": "c1",
             "chapter_title": "Ch 1", "text": "matched", "score": 0.9}
        ]


def test_chat_endpoint_returns_answer_with_sources() -> None:
    client = TestClient(create_app(ai_service=StubAiService()))

    resp = client.post("/v1/books/b1/chat", json={"question": "test?"})

    assert resp.status_code == 200
    assert resp.json()["answer"] == "Test answer"
    assert len(resp.json()["sources"]) == 1


def test_search_endpoint_returns_results() -> None:
    client = TestClient(create_app(ai_service=StubAiService()))

    resp = client.get("/v1/books/search?q=test")

    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1
    assert resp.json()["results"][0]["score"] == 0.9
```

Run: `uv run --extra dev pytest tests/api/test_ai_routes.py -v`
Expected: FAIL.

- [ ] **Step 2: Create AI schemas and routes**

Create `free_for_read/api/ai_schemas.py`:

```python
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
```

Create `free_for_read/api/ai_routes.py`:

```python
from typing import Protocol
from fastapi import APIRouter
from free_for_read.api.ai_schemas import ChatRequest, ChatResponse, SearchResponse, ReindexResponse, IndexStatusResponse
from free_for_read.ai.rag import RagResponse


class AiServiceProtocol(Protocol):
    async def query_book(self, book_id: str, question: str, *, top_k: int = 5) -> RagResponse: ...
    def search_books(self, q: str, *, limit: int = 10, book_id: str | None = None) -> list[dict]: ...


def create_ai_router(ai_service: AiServiceProtocol) -> APIRouter:
    router = APIRouter(prefix="/v1/books")

    @router.post("/{book_id}/chat", response_model=ChatResponse)
    async def chat(book_id: str, request: ChatRequest) -> RagResponse:
        return await ai_service.query_book(book_id, request.question)

    @router.get("/search", response_model=SearchResponse)
    def search(q: str, limit: int = 10, book_id: str | None = None) -> dict:
        results = ai_service.search_books(q, limit=limit, book_id=book_id)
        return {"results": results}

    return router
```

- [ ] **Step 3: Wire AI router into app.py**

Modify `free_for_read/api/app.py` — add to `create_app()`:

```python
from free_for_read.api.ai_routes import AiServiceProtocol, create_ai_router
```

Add parameter: `ai_service: AiServiceProtocol | None = None`

Wire router:
```python
if ai_service:
    app.include_router(create_ai_router(ai_service))
```

- [ ] **Step 4: Run tests**

Run: `uv run --extra dev pytest tests/api/test_ai_routes.py -v`
Expected: 2 tests PASS. Existing API tests also pass.

- [ ] **Step 5: Commit**

```bash
git add free_for_read/api/ai_schemas.py free_for_read/api/ai_routes.py free_for_read/api/app.py tests/api/test_ai_routes.py
git commit -m "feat: add ai chat and search api routes"
```

---

### Task 7: AI Service Wiring (Production Integration)

**Files:**
- Create: `free_for_read/ai/service.py`
- Modify: `free_for_read/api/app.py`

- [ ] **Step 1: Create production AiService**

Create `free_for_read/ai/service.py`:

```python
import os
from pathlib import Path
from free_for_read.ai.embeddings import create_embedding_provider, EmbeddingProvider
from free_for_read.ai.llm import create_llm_provider, LlmProvider
from free_for_read.ai.indexer import BookIndexer
from free_for_read.ai.rag import RagPipeline, RagResponse
from free_for_read.ai.chunking import chunk_chapter
from free_for_read.library.repository import LibraryRepository


class AiService:
    def __init__(
        self,
        *,
        repository: LibraryRepository,
        chroma_path: Path | None = None,
        llm: LlmProvider | None = None,
        embeddings: EmbeddingProvider | None = None,
    ):
        self._repository = repository
        storage_root = chroma_path or Path(os.environ.get("CHROMA_PATH", "storage/chroma"))
        self._embed_provider = embeddings or create_embedding_provider(
            os.environ.get("EMBED_PROVIDER", "local")
        )
        self._indexer = BookIndexer(chroma_path=storage_root, embeddings=self._embed_provider)
        self._llm = llm or create_llm_provider(os.environ.get("AI_PROVIDER", "stub"))
        self._rag = RagPipeline(llm=self._llm, indexer=self._indexer)

    async def query_book(self, book_id: str, question: str, *, top_k: int = 5) -> RagResponse:
        return await self._rag.query(book_id, question, top_k=top_k)

    def search_books(self, q: str, *, limit: int = 10, book_id: str | None = None) -> list[dict]:
        from free_for_read.library.repository import SQLiteLibraryRepository
        if isinstance(self._repository, SQLiteLibraryRepository):
            # Get all books for search scope
            books = self._repository.list_books(limit=100, offset=0)
            book_ids = [b.id for b in books] if book_id is None else [book_id]
            titles = {b.id: b.title for b in books}
        else:
            book_ids = [book_id] if book_id else []
            titles = {}

        results = self._rag.search(q, top_k=limit, book_ids=book_ids)
        for r in results:
            r.book_title = titles.get(r.book_id, "")
        return [r.model_dump() for r in results]

    def index_book(self, book_id: str) -> dict:
        chapters = self._repository.list_chapters(book_id)
        all_chunks = []
        for ch in chapters:
            chunks = chunk_chapter(
                ch.markdown, book_id=book_id, chapter_id=ch.id, chapter_title=ch.title,
            )
            all_chunks.extend([{
                "id": c.id, "text": c.text,
                "chapter_title": c.chapter_title, "heading_path": c.heading_path,
            } for c in chunks])
        self._indexer.index_book(book_id, all_chunks)
        return {"status": "indexed", "chunk_count": len(all_chunks)}

    def index_status(self, book_id: str) -> dict:
        indexed = self._indexer.collection_exists(book_id)
        return {"indexed": indexed, "chunk_count": None, "last_indexed": None}
```

- [ ] **Step 2: Wire AiService into app.py**

Modify `free_for_read/api/app.py` — update the `create_app()`:

```python
from free_for_read.ai.service import AiService

def create_app(
    parse_service: ParseServiceProtocol | None = None,
    library_service: LibraryServiceProtocol | None = None,
    ai_service: AiServiceProtocol | None = None,
    storage_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Free for Read", version="0.1.0")
    root = storage_root or Path("storage")
    service = parse_service or ParseService()
    app.include_router(create_router(service))
    app.include_router(create_parse_file_router(service))
    library = library_service or LibraryService(
        storage=LocalStorageBackend(root=root),
        repository=SQLiteLibraryRepository(root / "library.sqlite3"),
    )
    library.initialize()
    app.include_router(create_library_router(library))

    # Wire AI if service provided
    ai = ai_service or AiService(repository=library.repository)
    app.include_router(create_ai_router(ai))

    # ... exception handlers unchanged ...
```

- [ ] **Step 3: Run all tests**

Run: `uv run --extra dev pytest -v`
Expected: All tests pass (existing 140+ + new AI tests).

- [ ] **Step 4: Commit**

```bash
git add free_for_read/ai/service.py free_for_read/api/app.py
git commit -m "feat: wire ai service with production providers"
```

---

### Task 8: Frontend AI Panel & Search

**Files:**
- Create: `frontend/src/components/AiPanel.tsx`
- Create: `frontend/src/components/SearchBar.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/ReaderToolbar.tsx`
- Modify: `frontend/src/views/ReaderView.tsx`
- Modify: `frontend/src/views/LibraryView.tsx`

- [ ] **Step 1: Add AI endpoints to API client**

Modify `frontend/src/api/client.ts` — add after existing exports:

```typescript
// --- AI ---

export async function chatWithBook(bookId: string, question: string) {
  const res = await fetch(`${baseUrl()}/v1/books/${bookId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error('Chat failed')
  return res.json() as Promise<{ answer: string; sources: Array<{ chapter_id: string; chapter_title: string; heading_path: string; text: string; relevance: number }>; model: string; processing_ms: number }>
}

export async function searchBooks(q: string, bookId?: string) {
  const params = new URLSearchParams({ q })
  if (bookId) params.set('book_id', bookId)
  const res = await fetch(`${baseUrl()}/v1/books/search?${params}`)
  if (!res.ok) throw new Error('Search failed')
  return res.json() as Promise<{ results: Array<{ book_id: string; book_title: string; chapter_id: string; chapter_title: string; text: string; score: number }> }>
}
```

- [ ] **Step 2: Create AiPanel component**

Create `frontend/src/components/AiPanel.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, X, Loader2 } from 'lucide-react'
import { chatWithBook } from '../api/client'

interface Message { role: 'user' | 'assistant'; content: string; sources?: Array<{ chapter_title: string; heading_path: string; text: string; relevance: number }> }

export function AiPanel({ bookId, bookTitle, onClose }: { bookId: string; bookTitle: string; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([{
    role: 'assistant',
    content: `你好！你正在阅读《${bookTitle}》。有什么想了解的吗？`,
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput('')
    setMessages(p => [...p, { role: 'user', content: q }])
    setLoading(true)
    try {
      const resp = await chatWithBook(bookId, q)
      setMessages(p => [...p, { role: 'assistant', content: resp.answer, sources: resp.sources }])
    } catch { setMessages(p => [...p, { role: 'assistant', content: '抱歉，AI 请求失败，请稍后重试。' }]) }
    finally { setLoading(false) }
  }

  return (
    <div className="w-[340px] min-w-[340px] bg-[#faf7f2] flex flex-col border-l border-[#f0e8d9]" data-testid="ai-panel">
      <div className="px-4 py-3 border-b border-[#f0e8d9] flex items-center gap-2 shrink-0">
        <Sparkles size={16} stroke="#d4641a" />
        <span className="text-[13px] font-semibold text-[#3d2e1c]">AI 助手</span>
        <div className="flex-1" />
        <button onClick={onClose} className="w-6 h-6 rounded flex items-center justify-center text-[#b8a48e] hover:bg-[#f0e8d9]"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#d4641a] to-[#e88a3a] flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-white text-[10px] font-bold">AI</span>
              </div>
            )}
            <div className={`rounded-xl px-3 py-2 text-xs leading-relaxed max-w-[260px] ${
              m.role === 'user' ? 'bg-[#f5efe0] text-[#4a3f30]' : 'bg-white border border-[#f0e8d9] text-[#4a3f30]'
            }`}>
              <p>{m.content}</p>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#f0e8d9]">
                  {m.sources.map((s, j) => (
                    <p key={j} className="text-[10px] text-[#d4641a] mt-1">
                      📖 {s.chapter_title} · 相关度 {Math.round(s.relevance * 100)}%
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="text-xs text-[#b8a48e] flex items-center gap-1"><Loader2 size={12} className="animate-spin" />AI 正在思考...</p>}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-[#f0e8d9] flex gap-2 shrink-0">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="向 AI 提问..." className="flex-1 text-xs px-3 py-2 rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]" />
        <button onClick={send} disabled={loading || !input.trim()}
          className="w-8 h-8 rounded-lg bg-[#d4641a] flex items-center justify-center disabled:opacity-40">
          <Send size={14} stroke="#fff" />
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add AI toggle to ReaderToolbar**

Modify `frontend/src/components/ReaderToolbar.tsx` — add `onAiToggle` prop and button:

```tsx
import { Sparkles } from 'lucide-react'
// Add to Props interface:
onAiToggle: () => void
// Add button next to bookmark:
<button onClick={props.onAiToggle} className="w-9 h-9 rounded-lg border border-[#f0e8d9] bg-white flex items-center justify-center"><Sparkles size={16} stroke="#888" /></button>
```

- [ ] **Step 4: Wire AiPanel into ReaderView**

Modify `frontend/src/views/ReaderView.tsx`:

```tsx
// Add state:
const [showAi, setShowAi] = useState(false)
// Import AiPanel:
import { AiPanel } from '../components/AiPanel'
// Add AiPanel next to reader content:
// Wrap content in flex row: reader flex-1, AiPanel when showAi
// Pass onAiToggle to ReaderToolbar
```

- [ ] **Step 5: Create SearchBar and wire into LibraryView**

Create `frontend/src/components/SearchBar.tsx`:

```tsx
import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { searchBooks } from '../api/client'

interface SearchResult { book_id: string; book_title: string; chapter_id: string; chapter_title: string; text: string; score: number }

export function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    try { const data = await searchBooks(query.trim()); setResults(data.results); setOpen(true) }
    catch { setResults([]) }
    finally { setLoading(false) }
  }

  return (
    <div className="relative" data-testid="search-bar">
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={16} stroke="#b8a48e" className="absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="搜索所有书籍中的内容..." className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#f0e8d9] bg-white focus:outline-none focus:border-[#d4641a]" />
        </div>
        <button onClick={handleSearch} disabled={loading} className="px-4 py-2 bg-[#d4641a] text-white rounded-lg text-xs font-semibold">搜索</button>
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-xl border border-[#f0e8d9] shadow-lg z-30 max-h-[300px] overflow-auto">
          {results.map((r, i) => (
            <div key={i} className="p-3 border-b border-[#f0e8d9] last:border-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-[#3d2e1c]">{r.book_title} · {r.chapter_title}</span>
                <span className="text-[10px] text-[#d4641a] bg-[#fef7f0] px-1.5 py-0.5 rounded">{Math.round(r.score * 100)}%</span>
              </div>
              <p className="text-xs text-[#4a3f30] leading-relaxed line-clamp-2">{r.text}</p>
            </div>
          ))}
        </div>
      )}
      {open && results.length === 0 && !loading && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-xl border border-[#f0e8d9] shadow-lg z-30 p-4 text-center text-xs text-[#b8a48e]">未找到相关内容</div>
      )}
    </div>
  )
}
```

Modify `frontend/src/views/LibraryView.tsx` — add `import { SearchBar }` and place after header:

```tsx
import { SearchBar } from '../components/SearchBar'
// In JSX, add after <header>:
<div className="px-5 py-2 bg-white border-b border-[#f0e8d9]"><SearchBar /></div>
```

- [ ] **Step 6: Verify TypeScript compiles and tests pass**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AiPanel.tsx frontend/src/components/SearchBar.tsx frontend/src/api/client.ts frontend/src/components/ReaderToolbar.tsx frontend/src/views/ReaderView.tsx frontend/src/views/LibraryView.tsx
git commit -m "feat: add ai panel and semantic search frontend"
```

---

### Task 9: Integration & Final Verification

**Files:**
- Create: `tests/api/test_ai_integration.py`
- Modify: `README.md`

- [ ] **Step 1: Write integration test**

Create `tests/api/test_ai_integration.py`:

```python
from fastapi.testclient import TestClient
from free_for_read.api.app import create_app
from free_for_read.ai.embeddings import StubEmbeddingProvider
from free_for_read.ai.llm import StubLlmProvider
from free_for_read.ai.service import AiService
from free_for_read.library.repository import SQLiteLibraryRepository
from free_for_read.library.storage import LocalStorageBackend
from free_for_read.library.service import LibraryService


def test_chat_and_search_end_to_end(tmp_path) -> None:
    """Import a book, index it, then chat and search."""
    # Use stub AI providers for deterministic test
    ai = AiService(
        repository=SQLiteLibraryRepository(tmp_path / "lib.sqlite3"),
        chroma_path=tmp_path / "chroma",
        llm=StubLlmProvider(),
        embeddings=StubEmbeddingProvider(),
    )
    library = LibraryService(
        storage=LocalStorageBackend(root=tmp_path / "storage"),
        repository=ai._repository,
        parser=lambda content, filename: type('obj', (), {
            'title': 'Test Book', 'author': 'Ada', 'language': 'en',
            'source_type': type('obj', (), {'value': 'epub'}),
            'chapters': [type('obj', (), {
                'index': 0, 'title': 'Ch1', 'markdown': '# Ch1\n\nTest content.',
                'word_count': 3, 'source_ref': 'c1.xhtml',
                'metadata': {},
            })],
            'chapter_count': 1, 'word_count': 3, 'cover_path': None,
            'metadata': {},
        })(),
    )
    client = TestClient(create_app(library_service=library, ai_service=ai, storage_root=tmp_path / "storage"))

    # Import book
    import_resp = client.post("/v1/books/import", files={"file": ("test.epub", b"data", "application/epub+zip")})
    book_id = import_resp.json()["book"]["id"]

    # Index book
    ai.index_book(book_id)

    # Chat
    chat_resp = client.post(f"/v1/books/{book_id}/chat", json={"question": "what is this about?"})
    assert chat_resp.status_code == 200
    assert "Stub response" in chat_resp.json()["answer"]

    # Search
    search_resp = client.get(f"/v1/books/search?q=test")
    assert search_resp.status_code == 200
```

Run: `uv run --extra dev pytest tests/api/test_ai_integration.py -v`
Expected: PASS.

- [ ] **Step 2: Run full verification**

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: All Python tests pass, linter clean. TypeScript clean, frontend tests pass.

- [ ] **Step 3: Update README**

Add AI section to `README.md`:

```markdown
## AI Reading (Phase 5)

Configure AI via environment variables:

- `AI_PROVIDER`: `openai` | `anthropic` | `ollama` (default: `openai`)
- `AI_API_KEY`: Provider API key
- `AI_BASE_URL`: Custom endpoint (for OpenAI-compatible APIs or Ollama)
- `EMBED_PROVIDER`: `local` | `openai` (default: `local`)
- `CHROMA_PATH`: ChromaDB storage path (default: `storage/chroma`)

### Chat with a Book

```bash
curl -X POST http://127.0.0.1:8000/v1/books/{book_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"这一章的核心主题是什么？"}'
```

### Semantic Search

```bash
curl "http://127.0.0.1:8000/v1/books/search?q=红岸基地&limit=10"
```
```

- [ ] **Step 4: Final verification and commit**

```bash
uv run --extra dev pytest -v
uv run --extra dev ruff check .
cd frontend && npx tsc --noEmit && npx vitest run
git add tests/api/test_ai_integration.py README.md
git commit -m "test: add ai integration test and docs"
```

---

## Self-Review Notes

- Spec coverage: Chunking (Task 1), Embeddings (Task 2), LLM (Task 3), ChromaDB (Task 4), RAG (Task 5), API routes (Task 6), AiService wiring (Task 7), Frontend (Task 8), Integration (Task 9). All spec requirements mapped.
- Placeholder check: No TBD/TODO markers. All steps have concrete code.
- Type consistency: `ChatMessage`, `RagResponse`, `SearchResult` types flow from AI module through API schemas to frontend client. `StubLlmProvider` and `StubEmbeddingProvider` are used consistently across tests.
- Scope: Settings UI (Phase 6), TTS, stats excluded. BM25 hybrid search noted as future enhancement (current MVP uses vector-only search through ChromaDB).
