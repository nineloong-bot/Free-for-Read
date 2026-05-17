import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpcore
import httpx

from free_for_read.core.errors import ParseError


@dataclass(frozen=True)
class FetchedContent:
    url: str
    content: bytes
    content_type: str | None
    content_length: int | None


class UrlFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_bytes: int = 25 * 1024 * 1024,
        resolve_host_ips: Callable[[str], Iterable[str]] | None = None,
        network_backend: httpcore.AsyncNetworkBackend | None = None,
        max_redirects: int = 10,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.resolve_host_ips = resolve_host_ips or _default_resolve_host_ips
        self.network_backend = network_backend
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchedContent:
        current_url = self._validate_url(url, original_url=url)
        transport = _build_rebinding_safe_transport(
            resolve_host_ips=self.resolve_host_ips,
            network_backend=self.network_backend,
        )

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "FreeForRead/0.1"},
                transport=transport,
            ) as client:
                for _ in range(self.max_redirects + 1):
                    async with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if location is None:
                                response.raise_for_status()

                            current_url = self._validate_url(
                                urljoin(str(response.url), location),
                                original_url=url,
                            )
                            continue

                        response.raise_for_status()
                        content_length = _parse_content_length(
                            response.headers.get("content-length")
                        )
                        if content_length is not None and content_length > self.max_bytes:
                            _raise_content_too_large(url=url, max_bytes=self.max_bytes)

                        content = bytearray()
                        async for chunk in response.aiter_bytes(
                            chunk_size=max(1, self.max_bytes + 1)
                        ):
                            if len(content) + len(chunk) > self.max_bytes:
                                _raise_content_too_large(
                                    url=url,
                                    max_bytes=self.max_bytes,
                                )
                            content.extend(chunk)

                        return FetchedContent(
                            url=str(response.url),
                            content=bytes(content),
                            content_type=response.headers.get("content-type"),
                            content_length=content_length,
                        )

                raise ParseError(
                    code="fetch_failed",
                    message="Too many redirects while fetching source URL.",
                    details={"url": url, "max_redirects": self.max_redirects},
                )
        except httpx.TimeoutException as exc:
            raise ParseError(
                code="fetch_timeout",
                message="Timed out while fetching source URL.",
                details={"url": url},
            ) from exc
        except httpx.HTTPError as exc:
            raise ParseError(
                code="fetch_failed",
                message="Failed to fetch source URL.",
                details={"url": url},
            ) from exc

    def _validate_url(self, url: str, *, original_url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            _raise_invalid_url(url=original_url)

        hostname = parsed.hostname
        normalized_hostname = hostname.rstrip(".").lower()
        if normalized_hostname == "localhost" or normalized_hostname.endswith(
            ".localhost"
        ):
            _raise_invalid_url(url=original_url)

        try:
            direct_ip = ipaddress.ip_address(normalized_hostname)
        except ValueError:
            try:
                resolved_ips = list(self.resolve_host_ips(hostname))
            except OSError as exc:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"url": original_url, "hostname": hostname},
                ) from exc

            if not resolved_ips:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"url": original_url, "hostname": hostname},
                ) from None

            try:
                resolved_addresses = [
                    ipaddress.ip_address(resolved_ip) for resolved_ip in resolved_ips
                ]
            except ValueError as exc:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"url": original_url, "hostname": hostname},
                ) from exc
        else:
            resolved_addresses = [direct_ip]

        if any(_is_unsafe_ip(address) for address in resolved_addresses):
            _raise_invalid_url(url=original_url)

        return url


class _RebindingSafeAsyncNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(
        self,
        *,
        resolve_host_ips: Callable[[str], Iterable[str]],
        inner_backend: httpcore.AsyncNetworkBackend,
    ) -> None:
        self.resolve_host_ips = resolve_host_ips
        self.inner_backend = inner_backend

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        address = self._resolve_safe_connect_address(host)
        return await self.inner_backend.connect_tcp(
            address,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        return await self.inner_backend.connect_unix_socket(
            path,
            timeout=timeout,
            socket_options=socket_options,
        )

    async def sleep(self, seconds: float) -> None:
        await self.inner_backend.sleep(seconds)

    def _resolve_safe_connect_address(self, host: str) -> str:
        normalized_host = host.rstrip(".").lower()
        try:
            direct_ip = ipaddress.ip_address(normalized_host)
        except ValueError:
            try:
                resolved_ips = list(self.resolve_host_ips(host))
            except OSError as exc:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"hostname": host},
                ) from exc

            if not resolved_ips:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"hostname": host},
                ) from None

            try:
                addresses = [
                    ipaddress.ip_address(resolved_ip) for resolved_ip in resolved_ips
                ]
            except ValueError as exc:
                raise ParseError(
                    code="fetch_failed",
                    message="Failed to resolve source URL hostname.",
                    details={"hostname": host},
                ) from exc
        else:
            addresses = [direct_ip]

        if any(_is_unsafe_ip(address) for address in addresses):
            raise ParseError(
                code="invalid_url",
                message="Source URL is not allowed.",
                details={"hostname": host},
            )

        return str(addresses[0])


def _build_rebinding_safe_transport(
    *,
    resolve_host_ips: Callable[[str], Iterable[str]],
    network_backend: httpcore.AsyncNetworkBackend | None,
) -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport()
    pool = getattr(transport, "_pool", None)
    if pool is None or not hasattr(pool, "_network_backend"):
        raise RuntimeError(
            "Installed httpx/httpcore transport internals are incompatible with "
            "the rebinding-safe fetcher. Expected AsyncHTTPTransport._pool."
            "_network_backend."
        )

    inner_backend = network_backend or pool._network_backend
    pool._network_backend = _RebindingSafeAsyncNetworkBackend(
        resolve_host_ips=resolve_host_ips,
        inner_backend=inner_backend,
    )
    return transport


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _default_resolve_host_ips(hostname: str) -> Iterable[str]:
    return {
        result[4][0]
        for result in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    }


def _is_unsafe_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not address.is_global or address.is_multicast


def _raise_invalid_url(*, url: str) -> None:
    raise ParseError(
        code="invalid_url",
        message="Source URL is not allowed.",
        details={"url": url},
    )


def _raise_content_too_large(*, url: str, max_bytes: int) -> None:
    raise ParseError(
        code="content_too_large",
        message="Source content is larger than the configured limit.",
        details={"url": url, "max_bytes": max_bytes},
    )
