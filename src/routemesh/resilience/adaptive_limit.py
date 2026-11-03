"""Small AIMD/Vegas concurrency controller for backend admission."""

import asyncio
from dataclasses import dataclass, field


@dataclass(slots=True)
class AdaptiveConcurrencyLimit:
    """Adjust a backend's concurrency ceiling from latency and outcomes."""

    minimum: int = 1
    maximum: int = 100
    initial: int = 10
    target_latency_ms: float = 100.0
    additive_step: int = 1
    multiplicative_decrease: float = 0.7
    limit: int = 0
    in_flight: int = 0
    condition: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)

    def __post_init__(self) -> None:
        """Validate bounds and clamp the initial concurrency limit."""
        if self.minimum < 1 or self.maximum < self.minimum:
            raise ValueError("adaptive concurrency bounds are invalid")
        if self.target_latency_ms <= 0 or self.additive_step < 1:
            raise ValueError("latency target and additive step must be positive")
        if not 0 < self.multiplicative_decrease < 1:
            raise ValueError("multiplicative decrease must be between zero and one")
        self.limit = min(self.maximum, max(self.minimum, self.initial))

    async def acquire(self) -> None:
        """Wait for admission under the current dynamic concurrency ceiling."""
        async with self.condition:
            await self.condition.wait_for(lambda: self.in_flight < self.limit)
            self.in_flight += 1

    async def release(self) -> None:
        """Release one active request without allowing a negative count."""
        async with self.condition:
            self.in_flight = max(0, self.in_flight - 1)
            self.condition.notify_all()

    async def observe(self, latency_ms: float, succeeded: bool) -> int:
        """Increase cautiously on healthy latency; cut quickly on congestion."""
        if latency_ms < 0:
            raise ValueError("latency must be non-negative")
        async with self.condition:
            if not succeeded or latency_ms > self.target_latency_ms:
                self.limit = max(self.minimum, int(self.limit * self.multiplicative_decrease))
            elif latency_ms <= self.target_latency_ms * 0.8:
                self.limit = min(self.maximum, self.limit + self.additive_step)
            self.condition.notify_all()
            return self.limit

    async def reset(self) -> None:
        """Restore the initial limit while preserving currently active requests."""
        async with self.condition:
            self.limit = min(self.maximum, max(self.minimum, self.initial))
            self.condition.notify_all()
