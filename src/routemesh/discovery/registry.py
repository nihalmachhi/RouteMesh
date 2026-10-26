"""Event-loop-safe backend state registry."""

import asyncio
from dataclasses import replace
from datetime import datetime

from routemesh.discovery.models import BackendConfig, BackendSnapshot


class BackendRegistry:
    """Own backend snapshots and expose copy/update operations."""

    def __init__(self, backends: list[BackendConfig]) -> None:
        self._items = {
            backend.backend_id: BackendSnapshot(backend.backend_id, backend.url)
            for backend in backends
        }
        self._lock = asyncio.Lock()

    async def snapshots(self) -> list[BackendSnapshot]:
        """Return detached copies so callers cannot mutate registry state."""
        async with self._lock:
            return [replace(item) for item in self._items.values()]

    async def update_health(
        self,
        backend_id: str,
        healthy: bool,
        cpu_percent: float,
        checked_at: datetime,
        failure_threshold: int = 1,
        recovery_successes: int = 1,
        in_flight: int | None = None,
    ) -> None:
        """Update health state and consecutive check counters."""
        async with self._lock:
            backend = self._items[backend_id]
            if healthy:
                backend.consecutive_health_successes += 1
                backend.consecutive_health_failures = 0
                if backend.consecutive_health_successes >= recovery_successes:
                    backend.healthy = True
            else:
                backend.consecutive_health_failures += 1
                backend.consecutive_health_successes = 0
                if backend.consecutive_health_failures >= failure_threshold:
                    backend.healthy = False
            backend.cpu_percent = min(100.0, max(0.0, cpu_percent))
            if in_flight is not None:
                backend.in_flight = max(0, in_flight)
            backend.last_check_at = checked_at

    async def adjust_in_flight(self, backend_id: str, delta: int) -> int:
        """Atomically increment or decrement a backend's active request count."""
        async with self._lock:
            backend = self._items[backend_id]
            backend.in_flight = max(0, backend.in_flight + delta)
            return backend.in_flight

    async def set_draining(self, backend_id: str, draining: bool) -> BackendSnapshot:
        """Stop new routing to a backend while preserving its active requests."""
        async with self._lock:
            backend = self._items[backend_id]
            backend.draining = draining
            return replace(backend)

    async def update_runtime(
        self,
        backend_id: str,
        *,
        in_flight: int | None = None,
        ewma_latency_ms: float | None = None,
        error_rate: float | None = None,
        circuit_state: str | None = None,
    ) -> None:
        """Apply only the runtime fields supplied by a metrics or breaker update."""
        async with self._lock:
            backend = self._items[backend_id]
            if in_flight is not None:
                backend.in_flight = max(0, in_flight)
            if ewma_latency_ms is not None:
                backend.ewma_latency_ms = max(0.0, ewma_latency_ms)
            if error_rate is not None:
                backend.error_rate = min(1.0, max(0.0, error_rate))
            if circuit_state is not None:
                backend.circuit_state = circuit_state
