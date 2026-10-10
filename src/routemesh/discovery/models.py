"""Backend identity and mutable health snapshot types."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BackendConfig:
    """Immutable static backend endpoint configuration."""

    backend_id: str
    url: str


@dataclass(slots=True)
class BackendSnapshot:
    """Mutable operational state consumed by routing policies."""

    backend_id: str
    url: str
    healthy: bool = False
    circuit_state: str = "closed"
    in_flight: int = 0
    ewma_latency_ms: float = 0.0
    error_rate: float = 0.0
    cpu_percent: float = 0.0
    last_check_at: datetime | None = None
    consecutive_health_failures: int = 0
    consecutive_health_successes: int = 0
    extensions: dict[str, float] = field(default_factory=dict)
