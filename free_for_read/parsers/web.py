import re

import trafilatura
from bs4 import BeautifulSoup

from free_for_read.core.models import Document, DocumentNode, SourceType


class WebParser:
    source_type = SourceType.WEB

    def parse(self, content: bytes, *, source_url: str) -> Document:
        html = content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        root = DocumentNode(type="document")
        article = soup.find("article") or soup.find("main") or soup.body or soup

        for tag in article.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            text = _clean_text(tag.get_text(" ", strip=True))
            if not text:
                continue
            if tag.name and tag.name.startswith("h"):
                root.children.append(
                    DocumentNode(type="heading", text=text, level=int(tag.name[1]))
                )
            else:
                root.children.append(DocumentNode(type="paragraph", text=text))

        if not root.children:
            extracted = trafilatura.extract(html, url=source_url, output_format="txt") or ""
            root.children.extend(
                DocumentNode(type="paragraph", text=line.strip())
                for line in extracted.splitlines()
                if line.strip()
            )

        title = _first_heading(root) or _html_title(soup)
        return Document(root=root, title=title)


def _first_heading(root: DocumentNode) -> str | None:
    for child in root.children:
        if child.type == "heading" and child.text:
            return child.text
    return None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+([,.!?;:])", r"\1", value)


def _html_title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None
