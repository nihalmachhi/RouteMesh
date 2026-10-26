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
from routemesh.benchmarks.scenarios import SCENARIOS, Scenario
from routemesh.common.settings import get_settings

POLICIES = (
    "round_robin",
    "least_connections",
    "power_of_two_choices",
    "ewma_latency",
    "latency_aware",
    "thompson_sampling",
)
API_URL = os.getenv("ROUTEMESH_BENCHMARK_API", "http://localhost:8000")
DURATION = os.getenv("ROUTEMESH_BENCH_DURATION", "60s")


def _admin_client() -> httpx.Client:
    """Build an admin client without exposing credentials in dashboard code."""
    token = os.getenv("ROUTEMESH_ADMIN_TOKEN") or get_settings().admin_token
    if not token:
        raise RuntimeError("ROUTEMESH_ADMIN_TOKEN must be configured before running benchmarks")
    headers = {"X-RouteMesh-Admin-Token": token}
    return httpx.Client(base_url=API_URL, headers=headers, timeout=5.0)


def _set_policy(client: httpx.Client, policy: str) -> None:
    """Activate one registered policy before starting its identical run."""
    response = client.put("/admin/policy", json={"policy": policy})
    response.raise_for_status()


def _run_policy(output: Path, policy: str) -> dict[str, int | float]:
    """Run the fixed Locust profile and return its real aggregate CSV stats."""
    output.parent.mkdir(parents=True, exist_ok=True)
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
            DURATION,
            "--csv",
            str(output / policy),
            "--only-summary",
        ],
        check=True,
        env={**os.environ, "ROUTEMESH_TARGET_URL": API_URL},
    )
    return read_summary(output / (policy + "_stats.csv"))


def _behavior_payload(scenario: Scenario) -> dict[str, int | float | bool]:
    """Convert a scenario into validated demo backend controls."""
    return {
        "latency_ms": scenario.latency_ms,
        "jitter_ms": scenario.jitter_ms,
        "error_rate": scenario.error_rate,
        "cpu_percent": scenario.cpu_percent,
        "down": scenario.down,
        "flap_every": scenario.flap_every,
    }


def run() -> Path:
    """Run identical workloads under each policy and save raw and summarized data."""
    root = Path(__file__).resolve().parents[3]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = root / "output" / "benchmarks" / stamp
    output.mkdir(parents=True, exist_ok=False)
    scenario_names = tuple(
        item.strip()
        for item in os.getenv("ROUTEMESH_BENCH_SCENARIOS", ",".join(SCENARIOS)).split(",")
        if item.strip()
    )
    unknown = set(scenario_names) - SCENARIOS.keys()
    if not scenario_names or unknown:
        raise ValueError(f"unknown or empty benchmark scenarios: {sorted(unknown)}")
    summaries: dict[str, dict[str, dict[str, int | float]]] = {}
    with _admin_client() as client:
        original_policy = client.get("/admin/policy").json()["policy"]
        original_behavior = client.get("/admin/backends/backend-c/behavior").json()
        try:
            for scenario_name in scenario_names:
                scenario = SCENARIOS[scenario_name]
                summaries[scenario_name] = {}
                for policy in POLICIES:
                    client.post(
                        "/admin/backends/backend-c/behavior", json=_behavior_payload(scenario)
                    ).raise_for_status()
                    client.post("/admin/reset").raise_for_status()
                    _set_policy(client, policy)
                    summaries[scenario_name][policy] = _run_policy(
                        output / scenario_name, policy
                    )
        finally:
            client.post(
                "/admin/backends/backend-c/behavior", json=original_behavior
            ).raise_for_status()
            _set_policy(client, original_policy)
    conditions = {
        "scenarios": {name: _behavior_payload(SCENARIOS[name]) for name in scenario_names},
        "users": 30,
        "ramp_users_per_second": 5,
        "duration_per_policy": DURATION,
        "telemetry_reset_each_policy": "yes",
        "locust_seed": "not applicable; fixed workload has no randomized user actions",
        "machine": platform.platform(),
        "generated_at_utc": stamp,
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip(),
        "working_tree_dirty": bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        ),
    }
    report = {"results": summaries, "conditions": conditions}
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_comparison(summaries, output / "p95_comparison.png")
    render_comparison(summaries, root / "docs" / "benchmarks" / "policy-comparison.png")
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
            "| Scenario | Policy | Requests | Errors | Error rate | req/s | "
            "p50 ms | p95 ms | p99 ms |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario_name, policies in summaries.items():
        for policy, values in policies.items():
            rows.append(
                "| "
                + scenario_name
                + " | "
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
