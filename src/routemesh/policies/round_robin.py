"""Deterministic round-robin policy."""

from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class RoundRobinPolicy:
    """Select the next candidate using an injected rotation index."""

    name = "round_robin"

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
        context: dict[str, str] | None = None,
    ) -> RoutingDecision:
        """Rotate through the already filtered candidates without doing I/O."""
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        chosen = ordered[rotation % len(ordered)]
        scores = tuple(
            CandidateScore(
                item.backend_id,
                float(index),
                item.in_flight,
                item.ewma_latency_ms,
                item.cpu_percent,
                item.error_rate,
            )
            for index, item in enumerate(ordered)
        )
        return RoutingDecision(
            request_id,
            self.name,
            chosen.backend_id,
            "next healthy backend in rotation",
            scores,
            at,
        )
