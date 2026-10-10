"""Run controlled degraded-backend comparisons and publish measured results."""

import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from routemesh.benchmarks.report import read_summary, render_comparison

POLICIES = ("round_robin", "least_connections", "latency_aware")
API_URL = os.getenv("ROUTEMESH_BENCHMARK_API", "http://localhost:8000")


def _admin_client() -> httpx.Client:
    """Build an admin client without exposing credentials in dashboard code."""
    token = os.getenv("ROUTEMESH_ADMIN_TOKEN", "")
    headers = {"X-RouteMesh-Admin-Token": token} if token else {}
    return httpx.Client(base_url=API_URL, headers=headers, timeout=5.0)


def _set_policy(client: httpx.Client, policy: str) -> None:
    """Activate one registered policy before starting its identical run."""
    response = client.put("/admin/policy", json={"policy": policy})
    response.raise_for_status()


def _run_policy(output: Path, policy: str) -> dict[str, int | float]:
    """Run the fixed Locust profile and return its real aggregate CSV stats."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(Path(__file__).with_name("locustfile.py")),
            "--headless",
            "-u",
            "30",
            "-r",
            "5",
            "-t",
            "60s",
            "--seed",
            "42",
            "--csv",
            str(output / policy),
            "--only-summary",
        ],
        check=True,
        env={**os.environ, "ROUTEMESH_TARGET_URL": API_URL},
    )
    return read_summary(output / (policy + "_stats.csv"))


def run() -> Path:
    """Run identical workloads under each policy and save raw and summarized data."""
    root = Path(__file__).resolve().parents[3]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = root / "output" / "benchmarks" / stamp
    output.mkdir(parents=True, exist_ok=False)
    summaries: dict[str, dict[str, int | float]] = {}
    with _admin_client() as client:
        original_policy = client.get("/admin/policy").json()["policy"]
        control = {
            "latency_ms": 180,
            "jitter_ms": 0,
            "error_rate": 0.15,
            "cpu_percent": 90,
            "down": False,
        }
        client.post("/admin/backends/backend-c/behavior", json=control).raise_for_status()
        try:
            for policy in POLICIES:
                client.post("/admin/reset").raise_for_status()
                client.post("/admin/backends/backend-c/behavior", json=control).raise_for_status()
                _set_policy(client, policy)
                summaries[policy] = _run_policy(output, policy)
        finally:
            client.post(
                "/admin/backends/backend-c/behavior",
                json={
                    "latency_ms": 5,
                    "jitter_ms": 0,
                    "error_rate": 0,
                    "cpu_percent": 15,
                    "down": False,
                },
            ).raise_for_status()
            _set_policy(client, original_policy)
    conditions = {
        "scenario": "backend-c degraded (180 ms, 15% injected errors, 90% reported CPU)",
        "users": 30,
        "ramp_users_per_second": 5,
        "duration_per_policy": "60s",
        "telemetry_reset_each_policy": "yes",
        "locust_seed": 42,
        "machine": platform.platform(),
        "generated_at_utc": stamp,
    }
    report = {"results": summaries, "conditions": conditions}
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_comparison(summaries, output / "p95_comparison.png")
    public_report = root / "dashboard" / "public" / "benchmarks" / "results.json"
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    docs_report = root / "docs" / "benchmarks" / "results.md"
    rows = [
        "# Benchmark results",
        "",
        "Measured RouteMesh policy comparison. Raw Locust CSV and the p95 chart are in "
        + str(output.relative_to(root)).replace(chr(92), "/")
        + ".",
        "",
        "## Conditions",
        "",
    ]
    rows.extend("- " + key + ": " + str(value) for key, value in conditions.items())
    rows.extend(
        [
            "",
            "| Policy | Requests | Errors | Error rate | req/s | p50 ms | p95 ms | p99 ms |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for policy, values in summaries.items():
        rows.append(
            "| "
            + policy
            + " | "
            + str(values["requests"])
            + " | "
            + str(values["failures"])
            + " | "
            + format(values["error_rate"], ".4f")
            + " | "
            + format(values["rps"], ".2f")
            + " | "
            + format(values["p50_ms"], ".2f")
            + " | "
            + format(values["p95_ms"], ".2f")
            + " | "
            + format(values["p99_ms"], ".2f")
            + " |"
        )
    docs_report.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Measured Locust results written to {output}")
    return output


if __name__ == "__main__":
    run()
