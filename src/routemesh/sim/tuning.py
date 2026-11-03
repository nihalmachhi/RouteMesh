"""Deterministic random search for latency-aware policy weights."""

from statistics import mean, stdev
from typing import Any

from routemesh.core.prng import Mulberry32
from routemesh.sim.engine import simulate
from routemesh.sim.scenarios import scenario_backends


def tune_latency_weights(candidate_count: int = 20, seed: int = 77) -> dict[str, Any]:
    """Compare default weights to a seeded search on fixed synthetic runs."""
    if candidate_count < 1:
        raise ValueError("candidate count must be positive")
    random = Mulberry32(seed)
    seeds = tuple(range(400, 410))
    candidates = [{"w_latency": 0.5, "w_cpu": 0.3, "w_error": 0.2, "w_in_flight": 0.1}]
    for _ in range(candidate_count):
        latency = 0.2 + random.random() * 0.7
        cpu = random.random() * (1 - latency)
        candidates.append(
            {
                "w_latency": latency,
                "w_cpu": cpu,
                "w_error": 1 - latency - cpu,
                "w_in_flight": random.random() * 0.3,
            }
        )
    scored: list[tuple[float, dict[str, float], list[float]]] = []
    for weights in candidates:
        p99_values = [
            simulate(
                "latency_aware",
                scenario_backends("overloaded"),
                request_count=120,
                arrival_rate=35,
                seed=run_seed,
                weights=weights,
            )["p99_ms"]
            for run_seed in seeds
        ]
        scored.append((mean(p99_values), weights, p99_values))
    scored.sort(key=lambda item: (item[0], item[1]["w_latency"], item[1]["w_cpu"]))
    default = next(item for item in scored if item[1] == candidates[0])
    best = scored[0]
    sem = stdev(best[2]) / len(best[2]) ** 0.5 if len(best[2]) > 1 else 0.0
    return {
        "scenario": "overloaded",
        "seed_count": len(seeds),
        "candidate_count": candidate_count,
        "default": {
            "weights": default[1],
            "p99_ms_mean": default[0],
        },
        "tuned": {
            "weights": best[1],
            "p99_ms_mean": best[0],
            "p99_ms_ci95": [max(0.0, best[0] - 1.96 * sem), best[0] + 1.96 * sem],
        },
        "limitations": "Seeded search on a synthetic queue model; not production tuning evidence.",
    }
