"""Reproducible seeded routing scenarios for policy comparisons."""

from typing import Any


def standard_backends() -> list[dict[str, Any]]:
    """Return a small heterogeneous synthetic backend pool."""
    return [
        {
            "backend_id": "backend-a",
            "url": "http://backend-a:9001",
            "healthy": True,
            "circuit_state": "closed",
            "in_flight": 0,
            "ewma_latency_ms": 24.0,
            "cpu_percent": 22.0,
            "error_rate": 0.02,
            "failure_rate": 0.01,
        },
        {
            "backend_id": "backend-b",
            "url": "http://backend-b:9002",
            "healthy": True,
            "circuit_state": "closed",
            "in_flight": 0,
            "ewma_latency_ms": 58.0,
            "cpu_percent": 55.0,
            "error_rate": 0.04,
            "failure_rate": 0.04,
        },
        {
            "backend_id": "backend-c",
            "url": "http://backend-c:9003",
            "healthy": True,
            "circuit_state": "closed",
            "in_flight": 0,
            "ewma_latency_ms": 35.0,
            "cpu_percent": 34.0,
            "error_rate": 0.03,
            "failure_rate": 0.02,
        },
    ]


def scenario_backends(name: str) -> list[dict[str, Any]]:
    """Return baseline, overloaded, or failure-injection backend signals."""
    values = standard_backends()
    if name == "overloaded":
        values[0]["ewma_latency_ms"] = 180.0
        values[0]["cpu_percent"] = 92.0
    elif name == "flapping":
        values[1]["failure_rate"] = 0.35
        values[1]["ewma_latency_ms"] = 120.0
    elif name != "standard":
        raise ValueError(f"unknown simulation scenario: {name}")
    return values
