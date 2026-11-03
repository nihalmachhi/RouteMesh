import asyncio

import httpx
import pytest
from starlette.requests import Request

from routemesh.proxy.forwarder import HttpForwarder


@pytest.mark.asyncio
async def test_forwarder_preserves_query_body_and_request_id():
    seen = {}

    async def respond(request):
        seen["url"] = str(request.url)
        seen["body"] = await request.aread()
        seen["request_id"] = request.headers["x-request-id"]
        seen["forwarded_for"] = request.headers["x-forwarded-for"]
        seen["forwarded_proto"] = request.headers["x-forwarded-proto"]
        seen["forwarded_host"] = request.headers["x-forwarded-host"]
        return httpx.Response(
            201,
            stream=httpx.ByteStream(b"created"),
            headers=[("X-Upstream", "demo"), ("Set-Cookie", "a=1"), ("Set-Cookie", "b=2")],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/orders",
        "raw_path": b"/orders",
        "query_string": b"tag=a&tag=b",
        "root_path": "",
        "headers": [
            (b"host", b"client"),
            (b"x-hop", b"gone"),
            (b"connection", b"x-hop"),
            (b"x-forwarded-for", b"198.51.100.10"),
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-host", b"attacker.example"),
        ],
        "client": ("127.0.0.1", 12000),
        "server": ("client", 80),
    }
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": b"payload", "more_body": False}
        return {"type": "http.disconnect"}

    request = Request(scope, receive)
    response = await HttpForwarder(client, 1, 5, 1024).send(
        request, "http://backend", "orders", "request-1"
    )
    assert response.status_code == 201
    body = b"".join([chunk async for chunk in response.body_iterator])
    if response.background:
        await response.background()
    assert body == b"created"
    assert seen["url"] == "http://backend/orders?tag=a&tag=b"
    assert seen["body"] == b"payload"
    assert seen["request_id"] == "request-1"
    assert seen["forwarded_for"] == "127.0.0.1"
    assert seen["forwarded_proto"] == "http"
    assert seen["forwarded_host"] == "client"
    assert response.headers["x-upstream"] == "demo"
    assert response.headers.getlist("set-cookie") == ["a=1", "b=2"]
    await client.aclose()


@pytest.mark.asyncio
async def test_forwarder_preserves_gzip_wire_bytes_and_encoding_headers():
    compressed = b"\x1f\x8b\x08compressed-payload"

    async def respond(request):
        assert request.headers["accept-encoding"] == "gzip"
        return httpx.Response(
            200,
            stream=httpx.ByteStream(compressed),
            headers=[("Content-Encoding", "gzip"), ("Content-Length", str(len(compressed)))],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/asset",
            "raw_path": b"/asset",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"client"), (b"accept-encoding", b"gzip")],
            "client": ("127.0.0.1", 12000),
            "server": ("client", 80),
        },
        lambda: asyncio.sleep(0, result={"type": "http.request", "body": b"", "more_body": False}),
    )
    response = await HttpForwarder(client, 1, 5, 1024).send(
        request, "http://backend", "asset", "request-gzip"
    )
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == compressed
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["content-length"] == str(len(compressed))
    if response.background:
        await response.background()
    await client.aclose()


@pytest.mark.asyncio
async def test_forwarder_streams_request_and_rejects_body_over_limit():
    received = bytearray()

    async def respond(request):
        async for chunk in request.stream:
            received.extend(chunk)
        return httpx.Response(200, content=b"ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))

    def make_request(chunks, content_length=None):
        position = 0
        pulled = {"count": 0}
        headers = [(b"host", b"client")]
        if content_length is not None:
            headers.append((b"content-length", str(content_length).encode()))

        async def receive():
            nonlocal position
            if position >= len(chunks):
                return {"type": "http.disconnect"}
            chunk = chunks[position]
            position += 1
            pulled["count"] += len(chunk)
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": position < len(chunks),
            }

        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/upload",
                "raw_path": b"/upload",
                "query_string": b"",
                "root_path": "",
                "headers": headers,
                "client": ("127.0.0.1", 12000),
                "server": ("client", 80),
            },
            receive,
        ), pulled

    forwarder = HttpForwarder(client, 1, 5, 3 * 1024 * 1024)
    chunks = [b"x" * 1024 for _ in range(2 * 1024)]
    large_request, _ = make_request(chunks)
    response = await forwarder.send(large_request, "http://backend", "upload", "r1")
    assert response.status_code == 200
    assert len(received) == 2 * 1024 * 1024
    received.clear()
    over_limit_request, pulled = make_request([b"x" * 1024 for _ in range(4 * 1024)])
    response = await HttpForwarder(client, 1, 5, 1024).send(
        over_limit_request, "http://backend", "upload", "r2"
    )
    assert response.status_code == 413
    assert pulled["count"] <= 2048
    received.clear()
    small_request, _ = make_request([b"x" * 2048], 2048)
    response = await HttpForwarder(client, 1, 5, 1024).send(
        small_request, "http://backend", "upload", "r3"
    )
    assert response.status_code == 413
    assert received == b""
    await client.aclose()


@pytest.mark.asyncio
async def test_forwarder_returns_501_for_websocket_upgrade():
    called = False

    async def respond(request):
        nonlocal called
        called = True
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/socket",
            "raw_path": b"/socket",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"client"), (b"upgrade", b"websocket")],
            "client": ("127.0.0.1", 12000),
            "server": ("client", 80),
        },
        lambda: asyncio.sleep(0, result={"type": "http.request", "body": b"", "more_body": False}),
    )
    response = await HttpForwarder(client, 1, 5, 1024).send(
        request, "http://backend", "socket", "request-ws"
    )
    assert response.status_code == 501
    assert not called
    await client.aclose()


@pytest.mark.asyncio
async def test_forwarder_enforces_total_deadline_while_streaming_response():
    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(0.05)
            yield b"late"

    async def respond(request):
        return httpx.Response(200, stream=SlowStream())

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/slow",
            "raw_path": b"/slow",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"client")],
            "client": ("127.0.0.1", 12000),
            "server": ("client", 80),
        },
        lambda: asyncio.sleep(0, result={"type": "http.request", "body": b"", "more_body": False}),
    )
    response = await HttpForwarder(client, 1, 5, 1024, total_timeout=0.01).send(
        request, "http://backend", "slow", "request-slow"
    )
    with pytest.raises(TimeoutError):
        async for _ in response.body_iterator:
            pass
    if response.background:
        await response.background()
    await client.aclose()
