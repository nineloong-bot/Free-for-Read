from free_for_read.core.models import Document, DocumentNode
from free_for_read.renderers.markdown import render_markdown


def test_render_markdown_handles_headings_paragraphs_lists_tables_and_slides() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(type="heading", text="Title", level=1),
                DocumentNode(type="paragraph", text="Intro text."),
                DocumentNode(
                    type="list",
                    children=[
                        DocumentNode(type="list_item", text="First"),
                        DocumentNode(type="list_item", text="Second"),
                    ],
                ),
                DocumentNode(
                    type="table",
                    children=[
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="A"),
                                DocumentNode(type="table_cell", text="B"),
                            ],
                        ),
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="1"),
                                DocumentNode(type="table_cell", text="2"),
                            ],
                        ),
                    ],
                ),
                DocumentNode(
                    type="slide",
                    metadata={"slide_number": 2},
                    children=[
                        DocumentNode(type="heading", text="Slide Title", level=2),
                    ],
                ),
            ],
        )
    )

    assert render_markdown(document) == (
        "# Title\n\n"
        "Intro text.\n\n"
        "- First\n"
        "- Second\n\n"
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n\n"
        "---\n\n"
        "## Slide 2\n\n"
        "## Slide Title"
    )


def test_render_markdown_escapes_table_pipes_and_normalizes_ragged_rows() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(
                    type="table",
                    children=[
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="Name | Kind"),
                                DocumentNode(type="table_cell", text="Value"),
                            ],
                        ),
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="Alpha | Beta"),
                            ],
                        ),
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="One"),
                                DocumentNode(type="table_cell", text="Two"),
                                DocumentNode(type="table_cell", text="Ignored"),
                            ],
                        ),
                    ],
                )
            ],
        )
    )

    assert render_markdown(document) == (
        "| Name \\| Kind | Value |  |\n"
        "| --- | --- | --- |\n"
        "| Alpha \\| Beta |  |  |\n"
        "| One | Two | Ignored |"
    )


def test_render_markdown_preserves_body_cells_beyond_header_width() -> None:
    document = Document(
        root=DocumentNode(
            type="document",
            children=[
                DocumentNode(
                    type="table",
                    children=[
                        DocumentNode(
                            type="table_row",
                            children=[DocumentNode(type="table_cell", text="Only")],
                        ),
                        DocumentNode(
                            type="table_row",
                            children=[
                                DocumentNode(type="table_cell", text="A | B"),
                                DocumentNode(type="table_cell", text="Preserved"),
                            ],
                        ),
                    ],
                )
            ],
        )
    )

    assert render_markdown(document) == (
        "| Only |  |\n"
        "| --- | --- |\n"
        "| A \\| B | Preserved |"
    )
