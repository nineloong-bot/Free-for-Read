from free_for_read.parsers.web import WebParser
from free_for_read.renderers.markdown import render_markdown


def test_web_parser_extracts_title_headings_and_paragraphs() -> None:
    html = b"""
    <html>
      <head><title>Ignored Browser Title</title></head>
      <body>
        <nav>Navigation</nav>
        <main>
          <article>
            <h1>Clean Article</h1>
            <p>Hello <strong>reader</strong>.</p>
            <h2>Part One</h2>
            <p>Useful text.</p>
          </article>
        </main>
      </body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/article")

    assert document.title == "Clean Article"
    assert (
        render_markdown(document)
        == "# Clean Article\n\nHello reader.\n\n## Part One\n\nUseful text."
    )


def test_web_parser_uses_main_when_article_is_missing() -> None:
    html = b"""
    <html>
      <body>
        <nav>Navigation</nav>
        <main>
          <h1>Main Story</h1>
          <p>Main text.</p>
        </main>
      </body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/main")

    assert document.title == "Main Story"
    assert render_markdown(document) == "# Main Story\n\nMain text."


def test_web_parser_uses_body_when_article_and_main_are_missing() -> None:
    html = b"""
    <html>
      <head><title>Body Page</title></head>
      <body>
        <h1>Body Story</h1>
        <p>Body text.</p>
      </body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/body")

    assert document.title == "Body Story"
    assert render_markdown(document) == "# Body Story\n\nBody text."


def test_web_parser_uses_soup_when_body_is_missing() -> None:
    html = b"""
    <h1>Fragment Story</h1>
    <p>Fragment text.</p>
    """

    document = WebParser().parse(html, source_url="https://example.com/fragment")

    assert document.title == "Fragment Story"
    assert render_markdown(document) == "# Fragment Story\n\nFragment text."


def test_web_parser_uses_html_title_when_heading_is_missing() -> None:
    html = b"""
    <html>
      <head><title>Only Browser Title</title></head>
      <body>
        <article>
          <p>Paragraph only.</p>
        </article>
      </body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/title")

    assert document.title == "Only Browser Title"
    assert render_markdown(document) == "Paragraph only."


def test_web_parser_uses_trafilatura_when_no_nodes_are_found(monkeypatch) -> None:
    def extract_text(html: str, *, url: str, output_format: str) -> str:
        assert "No semantic nodes here" in html
        assert url == "https://example.com/fallback"
        assert output_format == "txt"
        return "Extracted line one.\n\nExtracted line two."

    monkeypatch.setattr("free_for_read.parsers.web.trafilatura.extract", extract_text)

    html = b"""
    <html>
      <head><title>Fallback Title</title></head>
      <body><section>No semantic nodes here</section></body>
    </html>
    """

    document = WebParser().parse(html, source_url="https://example.com/fallback")

    assert document.title == "Fallback Title"
    assert render_markdown(document) == "Extracted line one.\n\nExtracted line two."
