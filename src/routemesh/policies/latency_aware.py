"""Latency, CPU, and error aware policy with a load penalty."""

from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


def normalize(values: list[float]) -> list[float]:
    """Min-max normalize values, treating tied and singleton sets neutrally."""
    if not values or max(values) == min(values):
        return [0.0 for _ in values]
    low, span = min(values), max(values) - min(values)
    return [(value - low) / span for value in values]


def latency_signal(snapshot: BackendSnapshot, at: datetime, prior_ms: float = 50.0) -> float:
    """Bound latency to a stable scale and decay stale samples toward a neutral prior."""
    value = snapshot.ewma_latency_ms or prior_ms
    if snapshot.latency_updated_at is not None:
        age_seconds = max(0.0, (at - snapshot.latency_updated_at).total_seconds())
        decay = 0.5 ** (age_seconds / 30.0)
        value = prior_ms + (value - prior_ms) * decay
    return value / (value + 100.0)


class LatencyAwarePolicy:
    """Score candidates using normalized telemetry and an in-flight penalty."""

    name = "latency_aware"

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision:
        """Choose the lowest explainable score with stable tie-breaking."""
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        latencies = [latency_signal(item, at) for item in ordered]
        cpu = [min(100.0, max(0.0, item.cpu_percent)) / 100.0 for item in ordered]
        errors = [min(1.0, max(0.0, item.error_rate)) for item in ordered]
        loads = [max(0, item.in_flight) / (max(0, item.in_flight) + 10.0) for item in ordered]
        load_weight = weights.get("w_in_flight", 0.1)
        rows = []
        for item, latency, cpu_value, error, load in zip(
            ordered, latencies, cpu, errors, loads, strict=True
        ):
            score = (
                weights.get("w_latency", 0.5) * latency
                + weights.get("w_cpu", 0.3) * cpu_value
                + weights.get("w_error", 0.2) * error
                + load_weight * load
            )
            rows.append(
                CandidateScore(
                    item.backend_id,
                    score,
                    item.in_flight,
                    item.ewma_latency_ms,
                    item.cpu_percent,
                    item.error_rate,
                )
            )
        ranked = sorted(rows, key=lambda row: (row.score, row.in_flight, row.backend_id))
        chosen = ranked[0]
        return RoutingDecision(
            request_id,
            self.name,
            chosen.backend_id,
            f"lowest weighted score {chosen.score:.3f}; in-flight penalty mitigates herding",
            tuple(rows),
            at,
        )
