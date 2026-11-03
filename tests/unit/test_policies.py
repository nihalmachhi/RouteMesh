from datetime import UTC, datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.bandit import BanditRouter
from routemesh.policies.latency_aware import LatencyAwarePolicy, latency_signal, normalize
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.p2c import PowerOfTwoChoicesPolicy
from routemesh.policies.registry import create_policy_registry
from routemesh.policies.round_robin import RoundRobinPolicy
from routemesh.policies.weighted import SmoothWeightedRoundRobinPolicy, rendezvous_hash

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


def test_normalization_handles_tied_and_single_values():
    assert normalize([4.0, 4.0]) == [0.0, 0.0]
    assert normalize([7.0]) == [0.0]
    assert normalize([10.0, 20.0]) == [0.0, 1.0]


def test_latency_signal_uses_a_stable_scale_instead_of_per_request_minmax():
    low = BackendSnapshot("low", "http://low", True, ewma_latency_ms=1)
    close = BackendSnapshot("close", "http://close", True, ewma_latency_ms=2)
    slow = BackendSnapshot("slow", "http://slow", True, ewma_latency_ms=1000)
    close_gap = abs(latency_signal(close, NOW) - latency_signal(low, NOW))
    wide_gap = abs(latency_signal(slow, NOW) - latency_signal(low, NOW))
    assert close_gap < wide_gap


def test_stale_latency_sample_decays_toward_neutral_prior():
    from datetime import timedelta

    stale = BackendSnapshot(
        "slow",
        "http://slow",
        True,
        ewma_latency_ms=1000,
        latency_updated_at=NOW - timedelta(minutes=5),
    )
    assert latency_signal(stale, NOW) < latency_signal(stale, NOW - timedelta(minutes=5))


def test_power_of_two_choices_scores_only_a_stable_pair():
    values = candidates()
    decision = PowerOfTwoChoicesPolicy().select(
        values, request_id="stable", at=NOW, rotation=0, weights=WEIGHTS
    )
    repeated = PowerOfTwoChoicesPolicy().select(
        values, request_id="stable", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert decision == repeated
    assert len(decision.candidates) == 2
    assert "power-of-two" in decision.reason


def test_weighted_round_robin_honors_backend_weights_smoothly():
    values = [
        BackendSnapshot("a", "http://a", True, extensions={"weight": 2.0}),
        BackendSnapshot("b", "http://b", True, extensions={"weight": 1.0}),
    ]
    policy = SmoothWeightedRoundRobinPolicy()
    chosen = [
        policy.select(
            values, request_id=str(index), at=NOW, rotation=index, weights=WEIGHTS
        ).chosen_backend_id
        for index in range(30)
    ]
    assert chosen.count("a") == 20
    assert chosen.count("b") == 10
    assert rendezvous_hash("session", "a") == rendezvous_hash("session", "a")


def test_bandit_arms_explore_then_learn_and_report_regret():
    bandit = BanditRouter(("round_robin", "p2c"), strategy="ucb1")
    assert bandit.choose() == "round_robin"
    bandit.observe("round_robin", 0.2)
    assert bandit.choose() == "p2c"
    bandit.observe("p2c", 1.0)
    assert bandit.regret == 0.8
    assert bandit.choose() == "p2c"


def test_registered_bandit_policy_delegates_and_learns_from_route_reward():
    policies = create_policy_registry()
    policy = policies["bandit_ucb1"]
    decision = policy.select(
        candidates(), request_id="bandit-route", at=NOW, rotation=0, weights=WEIGHTS
    )
    assert decision.policy == "bandit_ucb1"
    assert decision.chosen_backend_id in {"a", "b"}
    policy.observe(decision, 0.8)
    assert sum(policy.selector.pulls.values()) == 1
