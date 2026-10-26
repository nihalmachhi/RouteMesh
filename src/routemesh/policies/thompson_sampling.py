"""Contextual Thompson sampling with bounded latency-and-error feedback."""

import math
import random
from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import CandidateScore, RoutingDecision


class ThompsonSamplingPolicy:
    """Learn backend success utility independently for request context buckets."""

    name = "thompson_sampling"

    def __init__(self) -> None:
        self._rng = random.Random(42)
        self._posterior: dict[str, dict[str, tuple[float, float]]] = {}

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
        """Sample a reward estimate for each arm in the request's context."""
        context_key = self._context_key(context)
        arms = self._posterior.setdefault(context_key, {})
        ordered = sorted(candidates, key=lambda item: item.backend_id)
        samples: dict[str, float] = {}
        for item in ordered:
            alpha, beta = arms.get(item.backend_id, (1.0, 1.0))
            samples[item.backend_id] = self._rng.betavariate(alpha, beta)
        chosen = max(ordered, key=lambda item: (samples[item.backend_id], item.backend_id))
        scores = tuple(
            CandidateScore(
                item.backend_id,
                1.0 - samples[item.backend_id],
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
            f"highest Thompson sample in {context_key}",
            scores,
            at,
            context_key,
        )

    def observe(
        self,
        context_key: str,
        backend_id: str,
        latency_ms: float,
        failed: bool,
        weights: dict[str, float],
    ) -> None:
        """Update one arm from observed request latency and failure outcome."""
        forgetting = weights["bandit_forgetting"]
        target_ms = weights["bandit_target_latency_ms"]
        error_penalty = weights["bandit_error_penalty"]
        arms = self._posterior.setdefault(context_key, {})
        for name, (alpha, beta) in tuple(arms.items()):
            arms[name] = (max(1.0, alpha * forgetting), max(1.0, beta * forgetting))
        alpha, beta = arms.get(backend_id, (1.0, 1.0))
        latency_reward = math.exp(-max(0.0, latency_ms) / target_ms)
        reward = latency_reward * (1.0 - error_penalty if failed else 1.0)
        arms[backend_id] = (alpha + reward, beta + 1.0 - reward)

    @staticmethod
    def _context_key(context: dict[str, str] | None) -> str:
        """Build a stable, bounded context key from fixed-cardinality features."""
        values = context or {}
        path_class = values.get("path_class", "other")
        size_class = values.get("size_class", "small")
        return f"path={path_class};size={size_class}"
