"""Backend drain state does not disturb in-flight work counters."""

import pytest

from routemesh.discovery.models import BackendConfig
from routemesh.discovery.registry import BackendRegistry


@pytest.mark.asyncio
async def test_drain_state_preserves_active_request_count():
    registry = BackendRegistry([BackendConfig("api", "http://localhost:8000")])
    await registry.adjust_in_flight("api", 3)
    snapshot = await registry.set_draining("api", True)
    assert snapshot.draining
    assert snapshot.in_flight == 3
    assert (await registry.snapshots())[0].draining

    await registry.set_draining("api", False)
    current = (await registry.snapshots())[0]
    assert not current.draining
    assert current.in_flight == 3
