"""Least-connections policy."""

from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class LeastConnectionsPolicy:
    """Select the healthy backend with the smallest in-flight count."""

    name = "least_connections"

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision:
        """Break equal-load ties by backend ID for reproducible decisions."""
        ordered = sorted(candidates, key=lambda item: (item.in_flight, item.backend_id))
        chosen = ordered[0]
        scores = tuple(
            CandidateScore(
                item.backend_id,
                float(item.in_flight),
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
            f"fewest in-flight requests ({chosen.in_flight})",
            scores,
            at,
        )
