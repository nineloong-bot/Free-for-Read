from free_for_read.core.models import Document, DocumentNode


def render_markdown(document: Document) -> str:
    return "\n\n".join(
        block for block in (_render_node(child) for child in document.root.children) if block
    ).strip()


def _render_node(node: DocumentNode) -> str:
    if node.type == "heading":
        level = max(1, min(node.level or 1, 6))
        return f"{'#' * level} {_clean(node.text)}"
    if node.type == "paragraph":
        return _clean(node.text)
    if node.type == "list":
        return "\n".join(f"- {_clean(child.text)}" for child in node.children)
    if node.type == "table":
        return _render_table(node)
    if node.type == "page_break":
        return "---"
    if node.type == "slide":
        slide_number = node.metadata.get("slide_number")
        title = f"## Slide {slide_number}" if slide_number is not None else "## Slide"
        body = "\n\n".join(
            block for block in (_render_node(child) for child in node.children) if block
        )
        return f"---\n\n{title}\n\n{body}".strip()
    if node.children:
        return "\n\n".join(
            block for block in (_render_node(child) for child in node.children) if block
        )
    return _clean(node.text)


def _render_table(node: DocumentNode) -> str:
    rows = [
        [_escape_table_cell(_clean(cell.text)) for cell in row.children]
        for row in node.children
    ]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    header = _normalize_table_row(rows[0], width)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend(
        "| " + " | ".join(_normalize_table_row(row, width)) + " |"
        for row in rows[1:]
    )
    return "\n".join(lines)


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _escape_table_cell(value: str) -> str:
    return value.replace("|", r"\|")


def _normalize_table_row(row: list[str], width: int) -> list[str]:
    return row + [""] * (width - len(row))
