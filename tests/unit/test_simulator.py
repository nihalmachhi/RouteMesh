from routemesh.core.prng import Mulberry32
from routemesh.sim.engine import simulate
from routemesh.sim.scenarios import scenario_backends


def test_mulberry32_is_repeatable_and_bounded():
    first = Mulberry32(42)
    second = Mulberry32(42)
    assert [first.random() for _ in range(8)] == [second.random() for _ in range(8)]
    assert all(0 <= value < 1 for value in [first.random() for _ in range(20)])


def test_policy_simulation_is_seeded_and_returns_comparable_metrics():
    first = simulate("p2c_peak_ewma", scenario_backends("flapping"), seed=912)
    second = simulate("p2c_peak_ewma", scenario_backends("flapping"), seed=912)
    assert first == second
    assert first["total"] == 60
    assert 0 <= first["error_rate"] <= 1
    assert first["p99_ms"] >= first["p50_ms"]
    assert sum(item["count"] for item in first["shares"]) <= first["total"]
