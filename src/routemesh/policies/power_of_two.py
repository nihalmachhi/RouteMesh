"""Power-of-two choices: sample two backends, then pick the lighter one."""

import hashlib
from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class PowerOfTwoPolicy:
    """Deterministically sample two choices per request and prefer lower load."""

    name = "power_of_two_choices"

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
        """Choose the least-loaded member of a stable, request-derived pair."""
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        if len(ordered) < 2:
            sampled = ordered
        else:
            digest = hashlib.blake2b(request_id.encode(), digest_size=8).digest()
            first = int.from_bytes(digest[:4], "big") % len(ordered)
            offset = 1 + int.from_bytes(digest[4:], "big") % (len(ordered) - 1)
            sampled = [ordered[first], ordered[(first + offset) % len(ordered)]]

        chosen = min(
            sampled,
            key=lambda item: (item.in_flight, item.ewma_latency_ms, item.backend_id),
        )
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
        pair = " and ".join(item.backend_id for item in sampled)
        return RoutingDecision(
            request_id,
            self.name,
            chosen.backend_id,
            f"lower in-flight load from sampled pair {pair}",
            scores,
            at,
        )
