"""Template-based natural-language explanations tied to decision fields."""

from routemesh.policies.base import RoutingDecision


def narrate_decision(decision: RoutingDecision) -> str:
    """Explain the recorded selected backend, policy reason, and candidate count."""
    return (
        f"{decision.policy} selected {decision.chosen_backend_id}: {decision.reason} "
        f"The decision compared {len(decision.candidates)} eligible candidate(s)."
    )
