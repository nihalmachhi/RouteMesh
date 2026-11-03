"""Export fixed policy decisions from RouteMesh's actual Python implementations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.registry import get_policy
from routemesh.sim.engine import simulate
from routemesh.sim.scenarios import scenario_backends

ROOT = Path(__file__).resolve().parents[2]

BACKEND_INPUTS = [
    {
        "backend_id": "backend-a",
        "url": "http://backend-a:9001",
        "healthy": True,
        "circuit_state": "closed",
        "in_flight": 2,
        "ewma_latency_ms": 24.0,
        "cpu_percent": 22.0,
        "error_rate": 0.02,
    },
    {
        "backend_id": "backend-b",
        "url": "http://backend-b:9002",
        "healthy": True,
        "circuit_state": "closed",
        "in_flight": 7,
        "ewma_latency_ms": 58.0,
        "cpu_percent": 55.0,
        "error_rate": 0.04,
    },
    {
        "backend_id": "backend-c",
        "url": "http://backend-c:9003",
        "healthy": True,
        "circuit_state": "closed",
        "in_flight": 4,
        "ewma_latency_ms": 35.0,
        "cpu_percent": 34.0,
        "error_rate": 0.03,
    },
]
WEIGHTS = {"w_latency": 0.5, "w_cpu": 0.3, "w_error": 0.2, "w_in_flight": 0.1}
REQUEST_ID = "fixture-001"
ROTATION = 1


def export() -> dict[str, Any]:
    """Build a JSON-serializable comparison with the real Python policy classes."""
    candidates = [BackendSnapshot(**row) for row in BACKEND_INPUTS]
    at = datetime(2026, 1, 1, tzinfo=UTC)
    decisions: dict[str, Any] = {}
    for name in ("round_robin", "least_connections", "latency_aware", "p2c_peak_ewma"):
        decision = get_policy(name).select(
            candidates,
            request_id=REQUEST_ID,
            at=at,
            rotation=ROTATION,
            weights=WEIGHTS,
        )
        decisions[name] = {
            "chosen_backend_id": decision.chosen_backend_id,
            "reason": decision.reason,
            "candidates": [
                {
                    "backend_id": score.backend_id,
                    "score": round(score.score, 9),
                    "in_flight": score.in_flight,
                }
                for score in decision.candidates
            ],
        }
    return {
        "request_id": REQUEST_ID,
        "rotation": ROTATION,
        "weights": WEIGHTS,
        "backends": BACKEND_INPUTS,
        "decisions": decisions,
    }


def main() -> None:
    """Write the generated fixture consumed by Vitest."""
    target = ROOT / "site/src/features/simulator/__fixtures__/policy-decisions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(export(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(ROOT)}")
    simulation_path = ROOT / "site/src/features/simulator/__fixtures__/simulation-standard-001.json"
    simulation_path.write_text(
        json.dumps(
            {
                "policy": "p2c_peak_ewma",
                "backends": scenario_backends("standard"),
                "request_count": 60,
                "arrival_rate": 30,
                "seed": 912,
                "result": simulate("p2c_peak_ewma", scenario_backends("standard"), seed=912),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {simulation_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
