"""Explicit routing policy registry."""

from routemesh.core.errors import ConfigurationError
from routemesh.policies.bandit import BanditRoutingPolicy
from routemesh.policies.base import RoutingPolicy
from routemesh.policies.latency_aware import LatencyAwarePolicy
from routemesh.policies.least_connections import LeastConnectionsPolicy
from routemesh.policies.p2c import PowerOfTwoChoicesPolicy
from routemesh.policies.round_robin import RoundRobinPolicy
from routemesh.policies.weighted import SmoothWeightedRoundRobinPolicy


def create_policy_registry() -> dict[str, RoutingPolicy]:
    """Create independent policy state for a single RouteMesh process."""
    base: dict[str, RoutingPolicy] = {
        "round_robin": RoundRobinPolicy(),
        "least_connections": LeastConnectionsPolicy(),
        "latency_aware": LatencyAwarePolicy(),
        "p2c_peak_ewma": PowerOfTwoChoicesPolicy(),
        "weighted_round_robin": SmoothWeightedRoundRobinPolicy(),
    }
    arms = tuple(base)
    base.update(
        {
            "bandit_epsilon_greedy": BanditRoutingPolicy(
                "bandit_epsilon_greedy", "epsilon_greedy", base, arms
            ),
            "bandit_ucb1": BanditRoutingPolicy("bandit_ucb1", "ucb1", base, arms),
            "bandit_thompson": BanditRoutingPolicy("bandit_thompson", "thompson", base, arms),
        }
    )
    return base


POLICIES = create_policy_registry()


def get_policy(name: str) -> RoutingPolicy:
    """Return a known policy or reject invalid runtime configuration."""
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ConfigurationError(f"unknown routing policy: {name}") from exc
