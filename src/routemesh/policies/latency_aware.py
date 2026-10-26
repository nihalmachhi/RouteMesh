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
        latencies = normalize([item.ewma_latency_ms for item in ordered])
        cpu = normalize([item.cpu_percent for item in ordered])
        errors = normalize([item.error_rate for item in ordered])
        loads = normalize([float(item.in_flight) for item in ordered])
        load_weight = weights.get("w_in_flight", 0.1)
        rows = []
        for item, latency, cpu_value, error, load in zip(
            ordered, latencies, cpu, errors, loads, strict=True
        ):
            score = (
                weights["w_latency"] * latency
                + weights["w_cpu"] * cpu_value
                + weights["w_error"] * error
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
