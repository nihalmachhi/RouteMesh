from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.requests import Request

from routemesh.core.errors import NoHealthyBackend
from routemesh.policies.base import RoutingDecision
from routemesh.proxy.router import ProxyRouter


class RetryBudgetStub:
    def start_request(self):
        pass

    def consume(self):
        return True


class BreakerStub:
    def release_probe(self):
        pass


@pytest.mark.asyncio
async def test_retry_returns_first_upstream_5xx_when_no_alternate_is_healthy():
    router = object.__new__(ProxyRouter)
    router.retry_budget = RetryBudgetStub()
    router.config = SimpleNamespace(retries={"max_attempts": 2})
    router.clock = SimpleNamespace(monotonic=lambda: 1.0)
    decision = RoutingDecision("r1", "round_robin", "backend-a", "test", (), datetime.now(UTC))
    router.choose = AsyncMock(
        side_effect=[(decision, "http://backend-a"), NoHealthyBackend("none")]
    )
    router._forward_once = AsyncMock(return_value=(httpx.Response(503), 0.01))
    router._record = AsyncMock()
    router.breakers = {"backend-a": BreakerStub()}
    request = Request(
        {
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
        }
    )

    response = await router.forward(request, "resource", "r1")

    assert response.status_code == 503
    router._record.assert_awaited_once()
