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
    book_id: str,
    chapter_id: str,
    chapter_title: str,
    *,
    target_tokens: int = 512,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    lines = markdown.splitlines()
    blocks: list[tuple[str | None, list[str]]] = []
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
        # Keep last block for overlap continuity
        if len(buffer) > 1:
            overlap_text = buffer[-1]
            overlap = _estimate_tokens(overlap_text)
            if overlap <= overlap_tokens:
                buffer = [overlap_text]
                buffer_tokens = overlap
                return
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
    return max(1, len(text) // 2)
