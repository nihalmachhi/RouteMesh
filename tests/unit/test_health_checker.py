from datetime import UTC, datetime

import httpx
import pytest

from routemesh.discovery.models import BackendConfig
from routemesh.discovery.registry import BackendRegistry
from routemesh.health.checker import HealthChecker


class FakeClock:
    def monotonic(self):
        return 1.0

    def utc_now(self):
        return datetime.now(UTC)


@pytest.mark.asyncio
async def test_health_checker_records_reported_load_separately():
    registry = BackendRegistry([BackendConfig("a", "http://a")])

    async def respond(request):
        return httpx.Response(200, json={"status": "ok", "cpu_percent": 30, "in_flight": 77})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        checker = HealthChecker(registry, 1, client, recovery_successes=1, clock=FakeClock())
        await checker._check_one("a", "http://a")

    snapshot = (await registry.snapshots())[0]
    assert snapshot.healthy
    assert snapshot.cpu_percent == 30
    assert snapshot.in_flight == 0
    assert snapshot.backend_reported_in_flight == 77


@pytest.mark.asyncio
async def test_health_checker_marks_backend_down_after_failed_response():
    registry = BackendRegistry([BackendConfig("a", "http://a")])

    async def respond(request):
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        checker = HealthChecker(registry, 1, client, failure_threshold=1, clock=FakeClock())
        await checker._check_one("a", "http://a")

    assert not (await registry.snapshots())[0].healthy
