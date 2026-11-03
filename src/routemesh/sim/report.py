"""Generate reproducible simulation comparisons and confidence intervals."""

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from routemesh.core.prng import Mulberry32
from routemesh.explain.narrate import narrate_decision
from routemesh.graph.topology import ServiceEdge, ServiceGraph
from routemesh.logmining.drain import DrainMiner
from routemesh.logmining.path_normalizer import normalize_path
from routemesh.policies.bandit import BanditRouter
from routemesh.policies.base import CandidateScore, RoutingDecision
from routemesh.sim.engine import simulate
from routemesh.sim.scenarios import scenario_backends
from routemesh.sim.tuning import tune_latency_weights

ROOT = Path(__file__).resolve().parents[3]
POLICIES = ("round_robin", "least_connections", "latency_aware", "p2c_peak_ewma")
SCENARIOS = ("standard", "overloaded", "flapping")
SEEDS = tuple(range(100, 120))


def build_report() -> dict[str, Any]:
    """Run identical fixed workloads for every policy and summarize p99/error."""
    comparisons: dict[str, Any] = {}
    for scenario in SCENARIOS:
        comparisons[scenario] = {}
        for policy in POLICIES:
            samples = [
                simulate(
                    policy,
                    scenario_backends(scenario),
                    request_count=120,
                    arrival_rate=35,
                    seed=seed,
                )
                for seed in SEEDS
            ]
            latencies = [item["p99_ms"] for item in samples]
            errors = [item["error_rate"] for item in samples]
            sem = statistics.stdev(latencies) / (len(latencies) ** 0.5) if len(latencies) > 1 else 0
            comparisons[scenario][policy] = {
                "p99_ms_mean": statistics.mean(latencies),
                "p99_ms_ci95": [
                    max(0.0, statistics.mean(latencies) - 1.96 * sem),
                    statistics.mean(latencies) + 1.96 * sem,
                ],
                "error_rate_mean": statistics.mean(errors),
                "seed_count": len(SEEDS),
            }
    graph = ServiceGraph(
        {"client", "gateway", "catalog", "inventory"},
        [
            ServiceEdge("client", "gateway", retries=1, latency_ms=5),
            ServiceEdge("gateway", "catalog", retries=2, latency_ms=20),
            ServiceEdge("catalog", "inventory", retries=1, latency_ms=40),
        ],
    )
    miner = DrainMiner()
    log_lines = [
        f"backend-a returned {status} in {duration}ms"
        for status, duration in ((503, 12), (502, 18), (503, 11), (200, 8))
    ]
    mined = [miner.add(line) for line in log_lines]
    decision = RoutingDecision(
        "report-001",
        "p2c_peak_ewma",
        "backend-a",
        "lower peak-EWMA/load score",
        (CandidateScore("backend-a", 0.1, 1, 20, 20, 0.0),),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    bandit = BanditRouter(
        ("round_robin", "least_connections", "latency_aware", "p2c_peak_ewma"),
        strategy="thompson",
        seed=88,
    )
    reward_random = Mulberry32(2026)
    expected_rewards = {
        "round_robin": 0.45,
        "least_connections": 0.55,
        "latency_aware": 0.7,
        "p2c_peak_ewma": 0.62,
    }
    for _ in range(200):
        arm = bandit.choose()
        bandit.observe(arm, float(reward_random.random() < expected_rewards[arm]))
    return {
        "schema_version": 1,
        "source": "seeded discrete-event simulation",
        "scenario_count": len(SCENARIOS),
        "seed_count": len(SEEDS),
        "request_count_per_run": 120,
        "comparisons": comparisons,
        "tuning": tune_latency_weights(),
        "retry_amplification": {
            "maximum_attempts_per_downstream_call": graph.retry_amplification("client"),
            "inventory_failure_blast_radius": list(graph.blast_radius("inventory")),
            "critical_path_ms": graph.critical_path_ms("client", "inventory"),
        },
        "bandit_evaluation": {
            "strategy": "Thompson sampling",
            "pulls": bandit.pulls,
            "observed_pseudo_regret": bandit.regret,
            "rounds": 200,
            "limitations": "Fixed synthetic reward probabilities, not live traffic feedback.",
        },
        "nlp_evaluation": {
            "input_lines": len(log_lines),
            "template_count": len(miner.templates()),
            "clustered_repeat_count": sum(not item.is_new for item in mined),
            "normalized_example_path": normalize_path("/orders/12345/items/987"),
            "decision_narration": narrate_decision(decision),
            "limitations": "Deterministic token rules; no semantic or free-form language model.",
        },
        "limitations": (
            "Synthetic queue model, not production performance or a live-proxy benchmark."
        ),
    }


def main() -> None:
    """Write a generated report under benchmarks/results and print its path."""
    output = ROOT / "benchmarks" / "results" / "policy-comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    encoded = json.dumps(report, indent=2) + "\n"
    output.write_text(encoded, encoding="utf-8")
    site_output = ROOT / "site" / "src" / "data" / "results.generated.json"
    site_output.parent.mkdir(parents=True, exist_ok=True)
    site_output.write_text(encoded, encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
