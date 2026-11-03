"""Deterministic policy workload simulator matching the browser's core model."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from typing import Any

from routemesh.core.prng import Mulberry32
from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.registry import get_policy


def percentile(values: list[float], point: float) -> float:
    """Return the nearest-rank percentile from finite ordered values."""
    if not values:
        return 0.0
    return values[min(len(values) - 1, max(0, ceil(point * len(values)) - 1))]


def simulate(
    policy: str,
    backends: list[dict[str, Any]],
    request_count: int = 60,
    arrival_rate: float = 30.0,
    seed: int = 2026,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Simulate arrivals, backend service times, and failures with a fixed seed."""
    count = max(1, min(120, int(request_count)))
    rate = max(1.0, min(100.0, float(arrival_rate)))
    random = Mulberry32(seed)
    values = [dict(item, in_flight=0) for item in backends]
    schedule: list[dict[str, Any]] = []
    by_id = {item["backend_id"]: item for item in values}
    served = {item["backend_id"]: 0 for item in values}
    histories: dict[str, list[bool]] = {item["backend_id"]: [] for item in values}
    failures = {item["backend_id"]: 0 for item in values}
    open_until = {item["backend_id"]: 0.0 for item in values}
    latencies: list[float] = []
    feed: list[dict[str, Any]] = []
    error_count = 0
    rotation = 0
    active_weights = weights or {
        "w_latency": 0.5,
        "w_cpu": 0.3,
        "w_error": 0.2,
        "w_in_flight": 0.1,
    }

    for index in range(count):
        now = index * 1000.0 / rate
        for position in range(len(schedule) - 1, -1, -1):
            completed = schedule[position]
            if completed["complete_at"] <= now:
                backend = by_id.get(completed["backend_id"])
                if backend is not None:
                    backend["in_flight"] = max(0, backend["in_flight"] - 1)
                schedule.pop(position)
        for backend in values:
            if (
                backend["healthy"]
                and backend["circuit_state"] == "open"
                and now >= open_until[backend["backend_id"]]
            ):
                backend["circuit_state"] = "half_open"
        candidates = [
            BackendSnapshot(
                backend_id=backend["backend_id"],
                url=backend["url"],
                healthy=backend["healthy"],
                circuit_state=backend["circuit_state"],
                in_flight=backend["in_flight"],
                ewma_latency_ms=backend["ewma_latency_ms"],
                cpu_percent=backend["cpu_percent"],
                error_rate=backend["error_rate"],
            )
            for backend in values
            if backend["healthy"] and backend["circuit_state"] != "open"
        ]
        request_id = f"req-{index + 1:03d}"
        if not candidates:
            error_count += 1
            feed.append(
                {
                    "request_id": request_id,
                    "backend_id": None,
                    "policy": policy,
                    "reason": "no healthy backend is currently eligible",
                    "succeeded": False,
                    "latency_ms": 0,
                }
            )
            continue
        decision = get_policy(policy).select(
            candidates,
            request_id=request_id,
            at=datetime(2026, 1, 1, tzinfo=UTC),
            rotation=rotation,
            weights=active_weights,
        )
        rotation += 1
        selected = by_id[decision.chosen_backend_id]
        selected["in_flight"] += 1
        served[selected["backend_id"]] += 1
        duration = max(
            1.0,
            selected["ewma_latency_ms"]
            * (0.82 + random.random() * 0.36)
            * (1 + selected["cpu_percent"] / 500),
        )
        succeeded = random.random() >= selected.get("failure_rate", 0.0)
        latencies.append(duration)
        if not succeeded:
            error_count += 1
        schedule.append({"backend_id": selected["backend_id"], "complete_at": now + duration})
        history = histories[selected["backend_id"]]
        history.append(succeeded)
        if len(history) > 20:
            history.pop(0)
        selected["error_rate"] = sum(not outcome for outcome in history) / len(history)
        streak = 0 if succeeded else failures[selected["backend_id"]] + 1
        failures[selected["backend_id"]] = streak
        if selected["circuit_state"] == "half_open":
            if succeeded:
                selected["circuit_state"] = "closed"
                failures[selected["backend_id"]] = 0
            else:
                selected["circuit_state"] = "open"
                open_until[selected["backend_id"]] = now + 10_000
        elif streak >= 5 or (len(history) >= 20 and selected["error_rate"] > 0.5):
            selected["circuit_state"] = "open"
            open_until[selected["backend_id"]] = now + 10_000
        feed.append(
            {
                "request_id": request_id,
                "backend_id": selected["backend_id"],
                "policy": policy,
                "reason": decision.reason,
                "succeeded": succeeded,
                "latency_ms": duration,
            }
        )
    latencies.sort()
    return {
        "policy": policy,
        "total": count,
        "errors": error_count,
        "error_rate": error_count / count,
        "p50_ms": percentile(latencies, 0.5),
        "p99_ms": percentile(latencies, 0.99),
        "shares": [
            {
                "backend_id": backend["backend_id"],
                "count": served[backend["backend_id"]],
                "percentage": served[backend["backend_id"]] / count * 100,
                "circuit_state": backend["circuit_state"],
            }
            for backend in values
        ],
        "feed": list(reversed(feed[-6:])),
    }
