"""Parse Locust CSV outputs and render honest comparison charts."""

import csv
from pathlib import Path
from typing import Any


def read_summary(path: Path) -> dict[str, int | float]:
    """Read aggregate request stats from a Locust *_stats.csv file."""
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    total = next((row for row in rows if row.get("Name") == "Aggregated"), None)
    if total is None:
        raise ValueError(f"Locust aggregate row is missing in {path}")
    requests = int(total.get("Request Count") or 0)
    failures = int(total.get("Failure Count") or 0)
    return {
        "requests": requests,
        "failures": failures,
        "error_rate": failures / requests if requests else 0.0,
        "rps": float(total.get("Requests/s") or 0),
        "p50_ms": float(total.get("50%") or 0),
        "p95_ms": float(total.get("95%") or 0),
        "p99_ms": float(total.get("99%") or 0),
    }


def render_comparison(results: dict[str, dict[str, Any]], output: Path) -> None:
    """Create a compact p95 chart from real Locust summaries only."""
    import matplotlib.pyplot as plt

    names = list(results)
    values = [results[name]["p95_ms"] for name in names]
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.bar(names, values, color="#526b7a")
    axis.set_ylabel("p95 latency (ms)")
    axis.set_title("RouteMesh policy comparison")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160)
    plt.close(figure)
