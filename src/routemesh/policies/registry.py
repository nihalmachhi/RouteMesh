"""Explicit routing policy registry."""

from routemesh.common.errors import ConfigurationError
from routemesh.policies.base import RoutingPolicy
from routemesh.policies.latency_aware import LatencyAwarePolicy
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.round_robin import RoundRobinPolicy

POLICIES: dict[str, RoutingPolicy] = {
    "round_robin": RoundRobinPolicy(),
    "least_connections": LeastConnectionsPolicy(),
    "latency_aware": LatencyAwarePolicy(),
}


def get_policy(name: str) -> RoutingPolicy:
    """Return a known policy or reject invalid runtime configuration."""
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ConfigurationError(f"unknown routing policy: {name}") from exc
