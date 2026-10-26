"""Choose the backend with the lowest observed EWMA request latency."""

from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class EwmaLatencyPolicy:
    """Route to the smallest observed EWMA, with deterministic ties."""

    name = "ewma_latency"

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
        """Choose the candidate with the lowest EWMA latency."""
        ordered = sorted(candidates, key=lambda item: (item.ewma_latency_ms, item.backend_id))
        chosen = ordered[0]
        scores = tuple(
            CandidateScore(
                item.backend_id,
                item.ewma_latency_ms,
                item.in_flight,
                item.ewma_latency_ms,
                item.cpu_percent,
                item.error_rate,
            )
            for item in ordered
        )
        return RoutingDecision(
            request_id,
            self.name,
            chosen.backend_id,
            f"lowest observed EWMA latency ({chosen.ewma_latency_ms:.1f} ms)",
            scores,
            at,
        )
