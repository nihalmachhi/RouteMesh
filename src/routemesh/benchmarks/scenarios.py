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
    jitter_ms: float = 0
    flap_every: int = 0


SLOW = Scenario("slow", 180, 0.0, 90)
FAILING = Scenario("failing", 10, 0.35, 75)
FLAPPING = Scenario("flapping", 15, 0.0, 70, flap_every=4)
SCENARIOS = {scenario.name: scenario for scenario in (SLOW, FAILING, FLAPPING)}
