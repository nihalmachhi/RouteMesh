"""HTTPX forwarding adapter and hop-by-hop header filtering."""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

HOP_BY_HOP_HEADERS = {
    "connection",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class RequestBodyTooLarge(Exception):
    """Signal that a streamed request exceeded its configured byte limit."""


def filtered_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers and any headers named by Connection."""
    connection_tokens = {
        token.strip().lower() for token in headers.get("connection", "").split(",") if token.strip()
    }
    excluded = HOP_BY_HOP_HEADERS | connection_tokens
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


def filtered_raw_headers(headers: Sequence[tuple[bytes, bytes]]) -> list[tuple[bytes, bytes]]:
    """Filter hop-by-hop fields while preserving valid repeated header fields."""
    decoded = [(key.lower(), value) for key, value in headers]
    connection_tokens = {
        token.strip().lower().encode("ascii")
        for key, value in decoded
        if key == b"connection"
        for token in value.decode("latin-1").split(",")
        if token.strip()
    }
    excluded = {name.encode("ascii") for name in HOP_BY_HOP_HEADERS} | connection_tokens
    return [(key.lower(), value) for key, value in headers if key.lower() not in excluded]


class HttpForwarder:
    """Forward request metadata and bytes with a shared AsyncClient."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        connect_timeout: float,
        read_timeout: float,
        max_body_bytes: int,
        total_timeout: float = 30.0,
        trusted_proxy_hosts: list[str] | None = None,
    ) -> None:
        self._client = client
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self._max_body_bytes = max_body_bytes
        self._total_timeout = total_timeout
        self._trusted_proxy_hosts = set(trusted_proxy_hosts or [])

    async def send(
        self, request: Request, backend_url: str, path: str, request_id: str
    ) -> Response:
        """Forward one bounded request and return a sanitized backend response."""
        if request.headers.get("upgrade", "").lower() == "websocket":
            return Response("WebSocket proxying is not supported", status_code=501)
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self._max_body_bytes:
            return Response("request body too large", status_code=413)
        headers = [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in filtered_raw_headers(request.headers.raw)
            if key.lower()
            not in {
                b"x-request-id",
                b"x-forwarded-for",
                b"x-forwarded-proto",
                b"x-forwarded-host",
            }
        ]
        headers.append(("X-Request-ID", request_id))
        client_host = request.client.host if request.client else "unknown"
        prior_forwarded_for = request.headers.get("x-forwarded-for")
        forwarded_for = (
            f"{prior_forwarded_for}, {client_host}"
            if client_host in self._trusted_proxy_hosts and prior_forwarded_for
            else client_host
        )
        headers.extend(
            [
                ("X-Forwarded-For", forwarded_for),
                ("X-Forwarded-Proto", request.url.scheme),
                ("X-Forwarded-Host", request.headers.get("host", "")),
            ]
        )
        target = f"{backend_url}/{path.lstrip('/')}"

        async def body_stream() -> AsyncIterator[bytes]:
            total = 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > self._max_body_bytes:
                    raise RequestBodyTooLarge
                if chunk:
                    yield chunk

        body_content: AsyncIterator[bytes] | bytes = body_stream()
        if request.method in {"GET", "HEAD", "OPTIONS"} and content_length in {None, "0"}:
            body_content = b""
        upstream_request = self._client.build_request(
            request.method,
            target,
            params=list(request.query_params.multi_items()),
            headers=headers,
            content=body_content,
            timeout=self._timeout,
        )
        try:
            async with asyncio.timeout(self._total_timeout):
                upstream = await self._client.send(upstream_request, stream=True)
        except RequestBodyTooLarge:
            return Response("request body too large", status_code=413)
        except TimeoutError as exc:
            raise httpx.TimeoutException("total upstream request deadline exceeded") from exc

        deadline = asyncio.get_running_loop().time() + self._total_timeout

        async def response_body() -> AsyncIterator[bytes]:
            async with asyncio.timeout_at(deadline):
                async for chunk in upstream.aiter_raw():
                    yield chunk

        response = StreamingResponse(
            response_body(),
            status_code=upstream.status_code,
            background=BackgroundTask(upstream.aclose),
        )
        response.raw_headers = filtered_raw_headers(upstream.headers.raw)
        return response
