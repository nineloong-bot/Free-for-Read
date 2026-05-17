from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from free_for_read.api.app import create_app
from free_for_read.core.service import ParseService
from free_for_read.fetchers.url_fetcher import UrlFetcher


def create_test_app():
    fetcher = UrlFetcher(resolve_host_ips=lambda hostname: ["93.184.216.34"])
    return create_app(parse_service=ParseService(fetcher=fetcher))


def test_parse_endpoint_parses_mocked_html_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/article",
        content=(
            b"<html><body><article><h1>Article</h1><p>Readable text.</p>"
            b"</article></body></html>"
        ),
        headers={"content-type": "text/html", "content-length": "85"},
    )
    client = TestClient(create_test_app())

    response = client.post("/v1/parse", json={"url": "https://example.com/article"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"] == "# Article\n\nReadable text."
    assert payload["document"]["root"]["children"][0]["type"] == "heading"
    assert payload["metadata"]["title"] == "Article"
    assert payload["metadata"]["source_type"] == "web"


def test_parse_endpoint_returns_unsupported_for_mocked_image_url(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/image.png",
        content=b"\x89PNG\r\n\x1a\n",
        headers={"content-type": "image/png", "content-length": "8"},
    )
    client = TestClient(create_test_app())

    response = client.post("/v1/parse", json={"url": "https://example.com/image.png"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_source_type"
