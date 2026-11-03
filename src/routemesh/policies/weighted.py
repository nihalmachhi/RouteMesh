"""Deterministic weighted routing strategies."""

import hashlib
from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class SmoothWeightedRoundRobinPolicy:
    """Use stable weighted slots to realize a smooth repeating distribution."""

    name = "weighted_round_robin"

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision:
        """Select by backend-specific configured weight with stable tie-breaking."""
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        slots = [
            item
            for item in ordered
            for _ in range(max(1, min(100, int(item.extensions.get("weight", 1)))))
        ]
        chosen_backend = slots[rotation % len(slots)]
        rows = tuple(
            CandidateScore(
                item.backend_id,
                0.0 if item.backend_id == chosen_backend.backend_id else 1.0,
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
            chosen_backend.backend_id,
            "selected from a deterministic weighted rotation",
            rows,
            at,
        )


def rendezvous_hash(key: str, backend_id: str) -> int:
    """Return a stable backend-specific hash for affinity routing."""
    digest = hashlib.blake2b(f"{key}:{backend_id}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big")
