"""Named repeatable benchmark scenarios and backend controls."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scenario:
    """One named backend failure or degradation profile."""

    name: str
    latency_ms: float
    error_rate: float
    cpu_percent: float
    down: bool = False


BASELINE = Scenario("baseline", 5, 0.0, 15)
DEGRADED = Scenario("degraded", 180, 0.15, 90)
UNAVAILABLE = Scenario("unavailable", 0, 1.0, 100, True)
