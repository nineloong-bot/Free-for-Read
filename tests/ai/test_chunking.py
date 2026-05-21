from free_for_read.ai.chunking import Chunk, chunk_chapter


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
        target_tokens=15,
    )

    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.book_id == "b1" for c in chunks)
    assert all(c.chapter_id == "c1" for c in chunks)
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
