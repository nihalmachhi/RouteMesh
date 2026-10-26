"""Factory registry for isolated routing policy instances."""

from collections.abc import Callable

from routemesh.common.errors import ConfigurationError
from routemesh.policies.base import RoutingPolicy
from routemesh.policies.ewma_latency import EwmaLatencyPolicy
from routemesh.policies.latency_aware import LatencyAwarePolicy
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.power_of_two import PowerOfTwoPolicy
from routemesh.policies.round_robin import RoundRobinPolicy
from routemesh.policies.thompson_sampling import ThompsonSamplingPolicy

POLICY_FACTORIES: dict[str, Callable[[], RoutingPolicy]] = {
    "round_robin": RoundRobinPolicy,
    "least_connections": LeastConnectionsPolicy,
    "power_of_two_choices": PowerOfTwoPolicy,
    "ewma_latency": EwmaLatencyPolicy,
    "latency_aware": LatencyAwarePolicy,
    "thompson_sampling": ThompsonSamplingPolicy,
}


def get_policy(name: str) -> RoutingPolicy:
    """Return a known policy or reject invalid runtime configuration."""
    try:
        return POLICY_FACTORIES[name]()
    except KeyError as exc:
        raise ConfigurationError(f"unknown routing policy: {name}") from exc


def create_policies() -> dict[str, RoutingPolicy]:
    """Create per-router policy instances so state never leaks across apps."""
    return {name: factory() for name, factory in POLICY_FACTORIES.items()}
