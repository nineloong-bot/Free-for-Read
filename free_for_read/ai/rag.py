import time

from pydantic import BaseModel

from free_for_read.ai.indexer import BookIndexer
from free_for_read.ai.llm import ChatMessage, LlmProvider

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

        results = self._indexer.query(book_id, question, top_k=top_k)

        if results:
            context_parts = []
            for r in results:
                context_parts.append(
                    f"[来源: {r['chapter_title']} > {r['heading_path']}]\n{r['text']}"
                )
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "（未找到相关内容）"

        user_content = f"参考以下内容回答问题：\n\n{context}\n\n问题：{question}"
        messages = [
            ChatMessage(role="system", content=RAG_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]

        answer = await self._llm.chat(messages)

        processing_ms = int((time.perf_counter() - started) * 1000)

        sources = []
        for r in results:
            sources.append({
                "chapter_id": r.get("chapter_id", ""),
                "chapter_title": r.get("chapter_title", ""),
                "heading_path": r.get("heading_path", ""),
                "text": r["text"][:200],
                "relevance": round(r.get("score", 0.0), 2),
            })

        return RagResponse(answer=answer, sources=sources, model="llm", processing_ms=processing_ms)

    def search(
        self, query_text: str, *, top_k: int = 10, book_ids: list[str] | None = None
    ) -> list[SearchResult]:
        if not book_ids:
            return []

        results: list[SearchResult] = []
        for book_id in book_ids:
            hits = self._indexer.query(book_id, query_text, top_k=top_k)
            for h in hits:
                results.append(SearchResult(
                    book_id=book_id,
                    book_title=h.get("book_title", ""),
                    chapter_id=h.get("chapter_id", ""),
                    chapter_title=h.get("chapter_title", ""),
                    text=h["text"][:200],
                    score=round(h.get("score", 0.0), 2),
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
