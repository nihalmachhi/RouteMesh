import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from routemesh.core.clock import Clock
from routemesh.core.errors import NoHealthyBackend
from routemesh.discovery.config_loader import load_config
from routemesh.discovery.registry import BackendRegistry
from routemesh.metrics.decision_log import DecisionLog
from routemesh.metrics.event_stream import EventStream
from routemesh.metrics.prometheus import ProxyMetrics
from routemesh.proxy.backpressure import BackpressureLimiter, Overloaded
from routemesh.proxy.forwarder import HttpForwarder
from routemesh.proxy.router import ProxyRouter, RetryBudget
from routemesh.proxy.routes_proxy import proxy_request


class FakeClock(Clock):
    def __init__(self):
        self.value = 10.0

    def monotonic(self):
        return self.value

    def utc_now(self):
        return datetime.now(UTC)


def request():
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/resource",
            "raw_path": b"/resource",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"client")],
            "client": ("127.0.0.1", 1000),
            "server": ("client", 80),
        },
        receive,
    )


@pytest.mark.asyncio
async def test_global_admission_slot_is_held_until_stream_body_finishes():
    async def body():
        yield b"part"

    class RouterStub:
        async def forward(self, incoming, path, request_id):
            return StreamingResponse(body())

    limiter = BackpressureLimiter(1)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/resource",
        "raw_path": b"/resource",
        "query_string": b"",
        "headers": [],
        "server": ("client", 80),
        "client": ("127.0.0.1", 1234),
        "app": SimpleNamespace(state=SimpleNamespace(limiter=limiter, router=RouterStub())),
    }
    response = await proxy_request(Request(scope), "resource")
    assert limiter.active == 1
    with pytest.raises(Overloaded):
        await limiter.acquire()
    assert b"".join([chunk async for chunk in response.body_iterator]) == b"part"
    assert limiter.active == 0


def make_router(handler):
    config, backends = load_config(Path("configs/routemesh.yaml"))
    registry = BackendRegistry(backends)
    forward_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    clock = FakeClock()
    router = ProxyRouter(
        registry,
        HttpForwarder(forward_client, 1, 5, 1024, total_timeout=2),
        config,
        ProxyMetrics(),
        DecisionLog(),
        EventStream(),
        clock,
    )
    return router, registry, forward_client


async def mark_healthy(registry):
    for backend in await registry.snapshots():
        await registry.update_health(
            backend.backend_id,
            True,
            10,
            datetime.now(UTC),
            recovery_successes=1,
        )


@pytest.mark.asyncio
async def test_proxy_routes_records_explanation_and_tracks_download_until_stream_end():
    async def respond(outbound):
        return httpx.Response(200, stream=httpx.ByteStream(b"streamed-answer"))

    router, registry, client = make_router(respond)
    await mark_healthy(registry)
    response = await router.forward(request(), "resource", "request-1")
    assert response.status_code == 200
    assert (await registry.snapshots())[0].in_flight == 1
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == b"streamed-answer"
    assert (await registry.snapshots())[0].in_flight == 0
    assert router.decisions.recent(1)[0]["request_id"] == "request-1"
    assert "routemesh_requests_total" in router.metrics.content().decode()
    await router.reset_observations()
    metrics_after_reset = router.metrics.content().decode()
    assert re.search(
        (
            r'routemesh_requests_total\{backend="backend-a",'
            r'policy="latency_aware",status_class="2xx"\} 1\.0'
        ),
        metrics_after_reset,
    )
    if response.background:
        await response.background()
    await client.aclose()


@pytest.mark.asyncio
async def test_proxy_retries_5xx_on_an_alternate_then_returns_last_response():
    backends_seen = []

    async def respond(outbound):
        backends_seen.append(str(outbound.url))
        return httpx.Response(503, stream=httpx.ByteStream(b"upstream unavailable"))

    router, registry, client = make_router(respond)
    await mark_healthy(registry)
    router.config.retries["budget_ratio"] = 1
    router.retry_budget = RetryBudget(1, clock=router.clock)
    response = await router.forward(request(), "resource", "request-2")
    assert response.status_code == 503
    assert len(backends_seen) == 2
    assert len(router.decisions.recent(10)) == 2
    if response.background:
        await response.background()
    await client.aclose()


@pytest.mark.asyncio
async def test_enabled_hedge_returns_fast_alternate_and_cancels_slow_primary():
    requests_seen = []

    async def respond(outbound):
        requests_seen.append(outbound.url.port)
        if outbound.url.port == 9001:
            await asyncio.sleep(0.1)
            return httpx.Response(503, content=b"slow primary")
        return httpx.Response(200, stream=httpx.ByteStream(b"fast alternate"))

    router, registry, client = make_router(respond)
    await mark_healthy(registry)
    router.config.hedging.update(enabled=True, delay_ms=1)
    router.config.retries["budget_ratio"] = 1
    router.retry_budget = RetryBudget(1, clock=router.clock)

    response = await router.forward(request(), "resource", "hedged-request")

    assert response.status_code == 200
    assert requests_seen == [9001, 9002]
    assert b"".join([chunk async for chunk in response.body_iterator]) == b"fast alternate"
    assert (await registry.snapshots())[0].in_flight == 0
    await client.aclose()


@pytest.mark.asyncio
async def test_bandit_policy_uses_real_route_and_records_reward():
    async def respond(outbound):
        return httpx.Response(200, stream=httpx.ByteStream(b"routed"))

    router, registry, client = make_router(respond)
    await mark_healthy(registry)
    await router.policy.select("bandit_ucb1")

    response = await router.forward(request(), "resource", "bandit-request")

    assert response.status_code == 200
    assert router.decisions.recent(1)[0]["policy"] == "bandit_ucb1"
    policy = router.policies["bandit_ucb1"]
    assert sum(policy.selector.pulls.values()) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_proxy_rethrows_last_transport_error_after_retry_budget_is_exhausted():
    async def fail(outbound):
        raise httpx.ConnectError("connection refused", request=outbound)

    router, registry, client = make_router(fail)
    await mark_healthy(registry)
    router.config.retries["budget_ratio"] = 1
    router.retry_budget = RetryBudget(1, clock=router.clock)
    with pytest.raises(httpx.ConnectError):
        await router.forward(request(), "resource", "request-3")
    await client.aclose()


@pytest.mark.asyncio
async def test_proxy_rejects_when_no_backend_is_healthy():
    async def respond(outbound):
        return httpx.Response(200)

    router, _, client = make_router(respond)
    with pytest.raises(NoHealthyBackend):
        await router.forward(request(), "resource", "request-4")
    await client.aclose()
