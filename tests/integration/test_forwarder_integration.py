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
        return httpx.Response(201, content=b"created", headers={"X-Upstream": "demo"})

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
        "headers": [(b"host", b"client"), (b"x-hop", b"gone"), (b"connection", b"x-hop")],
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
    assert seen["url"] == "http://backend/orders?tag=a&tag=b"
    assert seen["body"] == b"payload"
    assert seen["request_id"] == "request-1"
    assert response.headers["x-upstream"] == "demo"
    await client.aclose()
