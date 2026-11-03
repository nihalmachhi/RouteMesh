import pytest

from routemesh.sim.tuning import tune_latency_weights


def test_tuner_is_reproducible_and_reports_default_and_tuned_values():
    first = tune_latency_weights(candidate_count=3, seed=21)
    second = tune_latency_weights(candidate_count=3, seed=21)
    assert first == second
    assert first["seed_count"] == 10
    assert first["candidate_count"] == 3
    assert first["tuned"]["p99_ms_ci95"][0] <= first["tuned"]["p99_ms_mean"]
    assert first["tuned"]["p99_ms_ci95"][1] >= first["tuned"]["p99_ms_mean"]


def test_tuner_rejects_empty_candidate_budget():
    with pytest.raises(ValueError):
        tune_latency_weights(candidate_count=0)
