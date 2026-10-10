"""Periodic active health checks for static backend endpoints."""

import asyncio
import logging
from contextlib import suppress

import httpx

from routemesh.common.clock import Clock, SystemClock
from routemesh.discovery.registry import BackendRegistry

logger = logging.getLogger(__name__)


class HealthChecker:
    """Poll backend health endpoints and update registry health snapshots."""

    def __init__(
        self,
        registry: BackendRegistry,
        interval_s: float,
        client: httpx.AsyncClient,
        failure_threshold: int = 3,
        recovery_successes: int = 2,
        clock: Clock | None = None,
    ) -> None:
        self.registry = registry
        self.interval_s = interval_s
        self.client = client
        self.failure_threshold = failure_threshold
        self.recovery_successes = recovery_successes
        self.clock = clock or SystemClock()
        self._stop = asyncio.Event()

    async def run(self) -> None:
        """Run checks until application shutdown."""
        while not self._stop.is_set():
            await self.check_all()
            with suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)

    async def stop(self) -> None:
        """Request orderly checker shutdown."""
        self._stop.set()

    async def check_all(self) -> None:
        """Check all configured backend health endpoints concurrently."""
        backends = await self.registry.snapshots()
        await asyncio.gather(*(self._check_one(item.backend_id, item.url) for item in backends))

    async def _check_one(self, backend_id: str, url: str) -> None:
        """Apply one active health observation without failing other checks."""
        healthy = False
        cpu = 0.0
        in_flight = None
        try:
            response = await self.client.get(f"{url}/health")
            response.raise_for_status()
            payload = response.json()
            healthy = payload.get("status") == "ok"
            cpu = float(payload.get("cpu_percent", 0.0))
            in_flight = int(payload.get("in_flight", 0))
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning(
                "backend health check failed",
                extra={"backend_id": backend_id, "event": type(exc).__name__},
            )
        await self.registry.update_health(
            backend_id,
            healthy,
            cpu,
            self.clock.utc_now(),
            self.failure_threshold,
            self.recovery_successes,
            in_flight,
        )
