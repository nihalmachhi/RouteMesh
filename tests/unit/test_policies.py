from datetime import UTC, datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.ewma_latency import EwmaLatencyPolicy
from routemesh.policies.latency_aware import LatencyAwarePolicy, normalize
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.power_of_two import PowerOfTwoPolicy
from routemesh.policies.round_robin import RoundRobinPolicy
from routemesh.policies.thompson_sampling import ThompsonSamplingPolicy

NOW = datetime.now(UTC)
WEIGHTS = {"w_latency": 0.5, "w_cpu": 0.3, "w_error": 0.2, "w_in_flight": 0.1}


def candidates():
    return [
        BackendSnapshot("b", "http://b", True, in_flight=3, ewma_latency_ms=80, cpu_percent=60),
        BackendSnapshot("a", "http://a", True, in_flight=1, ewma_latency_ms=20, cpu_percent=20),
    ]


def test_round_robin_uses_injected_rotation_and_stable_order():
    selected = RoundRobinPolicy().select(
        candidates(), request_id="r", at=NOW, rotation=1, weights=WEIGHTS
    )
    assert selected.chosen_backend_id == "b"


def test_least_connections_breaks_ties_by_backend_id():
    values = candidates()
    values[0].in_flight = values[1].in_flight
    selected = LeastConnectionsPolicy().select(
        values, request_id="r", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert selected.chosen_backend_id == "a"


def test_latency_policy_scores_and_explains_choice():
    selected = LatencyAwarePolicy().select(
        candidates(), request_id="r", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert selected.chosen_backend_id == "a"
    assert selected.reason.startswith("lowest weighted score")


def test_ewma_policy_chooses_lowest_observed_latency():
    selected = EwmaLatencyPolicy().select(
        candidates(), request_id="r", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert selected.chosen_backend_id == "a"
    assert selected.reason.startswith("lowest observed EWMA")


def test_power_of_two_uses_a_stable_pair_and_prefers_lower_load():
    values = candidates()
    policy = PowerOfTwoPolicy()
    first = policy.select(values, request_id="request-1", at=NOW, rotation=0, weights=WEIGHTS)
    second = policy.select(values, request_id="request-1", at=NOW, rotation=0, weights=WEIGHTS)
    assert first == second
    assert first.chosen_backend_id == "a"
    assert "sampled pair" in first.reason


def test_power_of_two_handles_single_candidate():
    selected = PowerOfTwoPolicy().select(
        candidates()[:1], request_id="r", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert selected.chosen_backend_id == "b"


def test_thompson_sampling_learns_from_latency_and_errors():
    policy = ThompsonSamplingPolicy()
    context = {"path_class": "api", "size_class": "small"}
    first = policy.select(
        candidates(), request_id="initial", at=NOW, rotation=0, weights=WEIGHTS, context=context
    )
    assert first.context == "path=api;size=small"
    for _ in range(100):
        policy.observe(first.context, "b", 500, True, BANDIT_WEIGHTS)
        policy.observe(first.context, "a", 20, False, BANDIT_WEIGHTS)
    chosen = [
        policy.select(
            candidates(),
            request_id=f"learned-{index}",
            at=NOW,
            rotation=0,
            weights=WEIGHTS,
            context=context,
        ).chosen_backend_id
        for index in range(20)
    ]
    assert chosen.count("a") > chosen.count("b")
    other_context = policy.select(
        candidates(),
        request_id="other-context",
        at=NOW,
        rotation=0,
        weights=WEIGHTS,
        context={"path_class": "static", "size_class": "large"},
    )
    assert other_context.context == "path=static;size=large"


BANDIT_WEIGHTS = {
    **WEIGHTS,
    "bandit_target_latency_ms": 250,
    "bandit_error_penalty": 0.8,
    "bandit_forgetting": 0.99,
}


def test_normalization_handles_tied_and_single_values():
    assert normalize([4.0, 4.0]) == [0.0, 0.0]
    assert normalize([7.0]) == [0.0]
    assert normalize([10.0, 20.0]) == [0.0, 1.0]
