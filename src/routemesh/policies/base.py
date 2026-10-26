"""Interfaces and immutable values shared by pure routing policies."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from routemesh.discovery.models import BackendSnapshot


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """Explain a candidate's policy score and measured routing inputs."""

    backend_id: str
    score: float
    in_flight: int
    ewma_latency_ms: float
    cpu_percent: float
    error_rate: float


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Record the selected backend and the policy's explanation."""

    request_id: str
    policy: str
    chosen_backend_id: str
    reason: str
    candidates: tuple[CandidateScore, ...]
    at: datetime


class RoutingPolicy(Protocol):
    """A pure policy maps backend snapshots to a decision."""

    name: str

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision: ...
