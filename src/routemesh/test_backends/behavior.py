"""Mutable behavior settings for one controllable demo backend."""

import asyncio
from dataclasses import dataclass, replace


@dataclass(slots=True)
class BackendBehavior:
    """Runtime knobs configured by the admin dashboard."""

    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    error_rate: float = 0.0
    cpu_percent: float = 10.0
    down: bool = False
    in_flight: int = 0


class BehaviorState:
    """Serialize behavior updates and request counters."""

    def __init__(self) -> None:
        self.value = BackendBehavior()
        self.lock = asyncio.Lock()

    async def update(self, values: dict[str, object]) -> BackendBehavior:
        """Atomically replace the bounded control values."""
        async with self.lock:
            for key in ("latency_ms", "jitter_ms", "error_rate", "cpu_percent", "down"):
                if key in values:
                    setattr(self.value, key, values[key])
            return self.value

    async def snapshot(self) -> BackendBehavior:
        """Return a copy suitable for one request's behavior decision."""
        async with self.lock:
            return replace(self.value)
