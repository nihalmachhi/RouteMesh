import asyncio
from datetime import UTC, datetime

from routemesh.discovery.models import BackendConfig
from routemesh.discovery.registry import BackendRegistry


def test_backend_health_cannot_overwrite_proxy_measured_in_flight():
    async def scenario():
        registry = BackendRegistry([BackendConfig("backend-a", "http://backend-a")])
        await registry.adjust_in_flight("backend-a", 2)
        await registry.update_health(
            "backend-a", True, 10, datetime.now(UTC), backend_reported_in_flight=99
        )
        snapshot = (await registry.snapshots())[0]
        assert snapshot.in_flight == 2
        assert snapshot.backend_reported_in_flight == 99

    asyncio.run(scenario())
