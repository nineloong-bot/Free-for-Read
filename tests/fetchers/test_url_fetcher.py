from collections.abc import Iterable
from dataclasses import FrozenInstanceError

import httpcore
import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from free_for_read.core.errors import ParseError
from free_for_read.fetchers import url_fetcher
from free_for_read.fetchers.url_fetcher import FetchedContent, UrlFetcher


def safe_resolver(hostname: str) -> list[str]:
    return {
        "example.com": ["93.184.216.34"],
        "cdn.example.com": ["93.184.216.35"],
    }[hostname]


def test_fetched_content_is_frozen() -> None:
    result = FetchedContent(
        url="https://example.com/doc.html",
        content=b"<html>ok</html>",
        content_type="text/html",
        content_length=15,
    )

    with pytest.raises(FrozenInstanceError):
        result.url = "https://example.com/other.html"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_fetcher_returns_content_headers_and_final_url(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/doc.html",
        content=b"<html>ok</html>",
        headers={"content-type": "text/html", "content-length": "15"},
    )
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    result = await fetcher.fetch("https://example.com/doc.html")

    assert result.url == "https://example.com/doc.html"
    assert result.content == b"<html>ok</html>"
    assert result.content_type == "text/html"
    assert result.content_length == 15


@pytest.mark.asyncio
async def test_fetcher_returns_final_redirected_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/doc",
        status_code=302,
        headers={"location": "https://cdn.example.com/doc.html"},
    )
    httpx_mock.add_response(
        url="https://cdn.example.com/doc.html",
        content=b"<html>ok</html>",
        headers={"content-type": "text/html"},
    )
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    result = await fetcher.fetch("https://example.com/doc")

    assert result.url == "https://cdn.example.com/doc.html"
    assert result.content == b"<html>ok</html>"


@pytest.mark.asyncio
async def test_fetcher_sends_user_agent_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/doc.html", content=b"ok")
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    await fetcher.fetch("https://example.com/doc.html")

    request = httpx_mock.get_request(url="https://example.com/doc.html")
    assert request is not None
    assert request.headers["user-agent"] == "FreeForRead/0.1"


@pytest.mark.asyncio
async def test_fetcher_rejects_content_larger_than_limit(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        content=b"0123456789",
        headers={"content-type": "application/pdf", "content-length": "10"},
    )
    fetcher = UrlFetcher(max_bytes=5, resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"


@pytest.mark.asyncio
async def test_fetcher_rejects_body_larger_than_limit_without_content_length(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        content=b"0123456789",
        headers={"content-type": "application/pdf"},
    )
    fetcher = UrlFetcher(max_bytes=5, resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"


@pytest.mark.asyncio
async def test_fetcher_rejects_body_larger_than_limit_with_low_content_length(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        content=b"0123456789",
        headers={"content-type": "application/pdf", "content-length": "4"},
    )
    fetcher = UrlFetcher(max_bytes=5, resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"


@pytest.mark.asyncio
async def test_fetcher_rejects_streamed_body_larger_than_limit_without_buffering_all(
    httpx_mock: HTTPXMock,
) -> None:
    def stream_chunks():
        yield b"123"
        yield b"456"
        raise AssertionError("fetcher read beyond max_bytes")

    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        stream=IteratorStream(stream_chunks()),
        headers={"content-type": "application/pdf"},
    )
    fetcher = UrlFetcher(max_bytes=5, resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"


@pytest.mark.asyncio
async def test_fetcher_reads_stream_with_bounded_chunk_size_for_large_raw_chunk(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_chunk_sizes: list[int | None] = []
    original_aiter_bytes = httpx.Response.aiter_bytes

    async def recording_aiter_bytes(
        self: httpx.Response,
        chunk_size: int | None = None,
    ):
        seen_chunk_sizes.append(chunk_size)
        async for chunk in original_aiter_bytes(self, chunk_size=chunk_size):
            yield chunk

    monkeypatch.setattr(httpx.Response, "aiter_bytes", recording_aiter_bytes)
    httpx_mock.add_response(
        url="https://example.com/large.pdf",
        stream=IteratorStream([b"0123456789"]),
        headers={"content-type": "application/pdf"},
    )
    fetcher = UrlFetcher(max_bytes=5, resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/large.pdf")

    assert exc_info.value.code == "content_too_large"
    assert seen_chunk_sizes == [6]


@pytest.mark.asyncio
async def test_fetcher_maps_timeout_to_parse_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.TimeoutException("boom"))
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/slow")

    assert exc_info.value.code == "fetch_timeout"


@pytest.mark.asyncio
async def test_fetcher_maps_status_error_to_parse_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/missing",
        status_code=404,
    )
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/missing")

    assert exc_info.value.code == "fetch_failed"


@pytest.mark.asyncio
async def test_fetcher_maps_non_timeout_http_error_to_parse_error(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/unreachable")

    assert exc_info.value.code == "fetch_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "https://localhost/file",
        "https://app.localhost/file",
        "https://127.0.0.1/file",
        "https://10.0.0.1/file",
        "https://100.64.0.1/file",
        "https://224.0.0.1/file",
        "https://[ff02::1]/file",
        "/relative/path",
    ],
)
async def test_fetcher_rejects_unsafe_or_invalid_initial_urls(url: str) -> None:
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch(url)

    assert exc_info.value.code == "invalid_url"


@pytest.mark.asyncio
async def test_fetcher_rejects_hostname_resolving_to_private_ip() -> None:
    def private_resolver(hostname: str) -> list[str]:
        assert hostname == "example.com"
        return ["192.168.1.10"]

    fetcher = UrlFetcher(resolve_host_ips=private_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/file")

    assert exc_info.value.code == "invalid_url"


@pytest.mark.asyncio
async def test_fetcher_rejects_hostname_resolving_to_shared_cgnat_ip_before_connecting() -> None:
    inner_backend = RecordingNetworkBackend()

    def cgnat_resolver(hostname: str) -> list[str]:
        assert hostname == "example.com"
        return ["100.64.0.1"]

    fetcher = UrlFetcher(
        resolve_host_ips=cgnat_resolver,
        network_backend=inner_backend,
    )

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/file")

    assert exc_info.value.code == "invalid_url"
    assert inner_backend.tcp_connections == []


@pytest.mark.asyncio
async def test_fetcher_rejects_hostname_resolving_to_multicast_ip_before_connecting() -> None:
    inner_backend = RecordingNetworkBackend()

    def multicast_resolver(hostname: str) -> list[str]:
        assert hostname == "example.com"
        return ["224.0.0.1"]

    fetcher = UrlFetcher(
        resolve_host_ips=multicast_resolver,
        network_backend=inner_backend,
    )

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/file")

    assert exc_info.value.code == "invalid_url"
    assert inner_backend.tcp_connections == []


@pytest.mark.asyncio
async def test_fetcher_maps_dns_resolution_failure_to_fetch_failed() -> None:
    def failing_resolver(hostname: str) -> list[str]:
        assert hostname == "example.com"
        raise OSError("dns failed")

    fetcher = UrlFetcher(resolve_host_ips=failing_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/file")

    assert exc_info.value.code == "fetch_failed"


@pytest.mark.asyncio
async def test_fetcher_rejects_redirect_to_private_target_before_requesting_it(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/doc",
        status_code=302,
        headers={"location": "http://127.0.0.1/admin"},
    )
    fetcher = UrlFetcher(resolve_host_ips=safe_resolver)

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/doc")

    assert exc_info.value.code == "invalid_url"
    assert httpx_mock.get_request(url="http://127.0.0.1/admin") is None


class RecordingNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self) -> None:
        self.tcp_connections: list[tuple[str, int]] = []

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        self.tcp_connections.append((host, port))
        raise AssertionError("unsafe addresses must be blocked before connecting")

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise AssertionError("URL fetches should not use Unix sockets")

    async def sleep(self, seconds: float) -> None:
        return None


@pytest.mark.asyncio
async def test_fetcher_revalidates_dns_at_tcp_connect_before_connecting() -> None:
    resolved_addresses = iter((["93.184.216.34"], ["127.0.0.1"]))
    inner_backend = RecordingNetworkBackend()

    def rebinding_resolver(hostname: str) -> list[str]:
        assert hostname == "example.com"
        return next(resolved_addresses)

    fetcher = UrlFetcher(
        resolve_host_ips=rebinding_resolver,
        network_backend=inner_backend,
    )

    with pytest.raises(ParseError) as exc_info:
        await fetcher.fetch("https://example.com/file")

    assert exc_info.value.code == "invalid_url"
    assert inner_backend.tcp_connections == []


def test_rebinding_safe_transport_raises_clear_error_for_incompatible_internals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class IncompatibleTransport:
        pass

    monkeypatch.setattr(
        url_fetcher.httpx,
        "AsyncHTTPTransport",
        IncompatibleTransport,
    )

    with pytest.raises(RuntimeError, match="incompatible") as exc_info:
        url_fetcher._build_rebinding_safe_transport(
            resolve_host_ips=safe_resolver,
            network_backend=None,
        )

    assert "httpx/httpcore transport internals" in str(exc_info.value)
