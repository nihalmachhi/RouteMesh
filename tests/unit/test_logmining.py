from datetime import UTC, datetime

import pytest

from routemesh.explain.narrate import narrate_decision
from routemesh.logmining.drain import DrainMiner
from routemesh.logmining.path_normalizer import normalize_path
from routemesh.policies.base import CandidateScore, RoutingDecision


def test_drain_miner_merges_variables_and_flags_new_templates():
    miner = DrainMiner()
    first = miner.add("backend-a returned 503 in 12ms")
    repeated = miner.add("backend-a returned 504 in 18ms")
    new_template = miner.add("circuit opened for backend-a")
    assert first.is_new
    assert not repeated.is_new
    assert repeated.template_id == first.template_id
    assert repeated.template == "backend-a returned * in *"
    assert new_template.is_new
    assert miner.templates()[0].count == 2


def test_drain_miner_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        DrainMiner(depth=0)


def test_path_normalization_bounds_dynamic_labels():
    value = "/users/123/orders/ab12?include=all"
    assert normalize_path(value) == "/users/{id}/orders/ab12"
    assert normalize_path("/users/123e4567-e89b-12d3-a456-426614174000") == "/users/{id}"


def test_narration_uses_decision_fields_and_candidate_count():
    decision = RoutingDecision(
        "req-1",
        "p2c_peak_ewma",
        "backend-a",
        "peak score 0.125 from 2 choices",
        (
            CandidateScore("backend-a", 0.125, 1, 20, 30, 0.0),
            CandidateScore("backend-b", 0.5, 3, 80, 50, 0.1),
        ),
        datetime.now(UTC),
    )
    explanation = narrate_decision(decision)
    for expected in ("p2c_peak_ewma", "backend-a", "0.125", "2 choices", "2 eligible"):
        assert expected in explanation
