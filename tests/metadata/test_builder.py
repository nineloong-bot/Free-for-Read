from free_for_read.core.models import Document, DocumentNode, SourceType
from free_for_read.metadata.builder import build_metadata


def test_build_metadata_counts_words_and_preserves_source_fields() -> None:
    document = Document(
        root=DocumentNode(type="document"),
        title="A Tale",
    )

    metadata = build_metadata(
        document=document,
        markdown="# A Tale\n\nHello clean world.",
        source_url="https://example.com/tale.html",
        source_type=SourceType.WEB,
        processing_ms=42,
        content_length=128,
    )

    assert metadata.title == "A Tale"
    assert metadata.source_url == "https://example.com/tale.html"
    assert metadata.source_type == SourceType.WEB
    assert metadata.word_count == 5
    assert metadata.processing_ms == 42
    assert metadata.content_length == 128


def test_build_metadata_counts_one_character_and_cjk_tokens() -> None:
    document = Document(root=DocumentNode(type="document"))

    metadata = build_metadata(
        document=document,
        markdown="I am a reader.\n\n我 爱 你\n\n我爱阅读",
        source_url="https://example.com/story.html",
        source_type=SourceType.WEB,
        processing_ms=10,
        content_length=None,
    )

    assert metadata.word_count == 8
