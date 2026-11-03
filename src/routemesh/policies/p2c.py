"""Power-of-two choices using peak-EWMA and live proxy load."""

from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class PowerOfTwoChoicesPolicy:
    """Compare two stable candidates instead of scoring the whole pool."""

    name = "p2c_peak_ewma"

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision:
        """Choose the lower-load, lower-peak-latency candidate from a pair."""
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        key = f"{request_id}:{rotation}".encode()
        first = 2166136261
        for byte in key:
            first = ((first ^ byte) * 16777619) & 0xFFFFFFFF
        first %= len(ordered)
        choices = [ordered[first], ordered[(first + 1) % len(ordered)]]
        latency_weight = weights.get("w_latency", 0.5)
        load_weight = weights.get("w_in_flight", 0.1)
        rows = [
            CandidateScore(
                item.backend_id,
                latency_weight * item.ewma_latency_ms / (item.ewma_latency_ms + 100)
                + load_weight * item.in_flight / (item.in_flight + 10),
                item.in_flight,
                item.ewma_latency_ms,
                item.cpu_percent,
                item.error_rate,
            )
            for item in choices
        ]
        chosen = min(rows, key=lambda row: (row.score, row.in_flight, row.backend_id))
        return RoutingDecision(
            request_id,
            self.name,
            chosen.backend_id,
            f"power-of-two choice: lower peak-EWMA/load score {chosen.score:.3f}",
            tuple(rows),
            at,
        )
