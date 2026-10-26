from datetime import UTC, datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.latency_aware import LatencyAwarePolicy, normalize
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.round_robin import RoundRobinPolicy

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
