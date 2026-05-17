from free_for_read.core.models import Document, DocumentNode


def test_document_node_serializes_nested_children() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(type="heading", text="Chapter 1", level=1),
                DocumentNode(type="paragraph", text="The first paragraph."),
            ],
        ),
        title="Novel",
    )

    payload = document.model_dump()

    assert payload["title"] == "Novel"
    assert payload["root"]["children"][0]["type"] == "heading"
    assert payload["root"]["children"][0]["level"] == 1
