"""HTTPX forwarding adapter and hop-by-hop header filtering."""

from collections.abc import Mapping

import httpx
from fastapi import Request, Response

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


def filtered_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers and any headers named by Connection."""
    connection_tokens = {
        token.strip().lower() for token in headers.get("connection", "").split(",") if token.strip()
    }
    excluded = HOP_BY_HOP_HEADERS | connection_tokens
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


class HttpForwarder:
    """Forward request metadata and bytes with a shared AsyncClient."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        connect_timeout: float,
        read_timeout: float,
        max_body_bytes: int,
    ) -> None:
        self._client = client
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self._max_body_bytes = max_body_bytes

    async def send(
        self, request: Request, backend_url: str, path: str, request_id: str
    ) -> Response:
        """Forward one bounded request and return a sanitized backend response."""
        body = await request.body()
        if len(body) > self._max_body_bytes:
            return Response("request body too large", status_code=413)
        headers = filtered_headers(request.headers)
        headers["X-Request-ID"] = request_id
        client_host = request.client.host if request.client else "unknown"
        previous = request.headers.get("x-forwarded-for")
        headers["X-Forwarded-For"] = f"{previous}, {client_host}" if previous else client_host
        target = f"{backend_url}/{path.lstrip('/')}"
        upstream = await self._client.request(
            request.method,
            target,
            params=list(request.query_params.multi_items()),
            headers=headers,
            content=body,
            timeout=self._timeout,
        )
        response_headers = filtered_headers(upstream.headers)
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )
