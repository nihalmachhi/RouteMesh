"""Small online policy selectors with explicit reward observations."""

import math
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from routemesh.discovery.models import BackendSnapshot
from routemesh.policies.base import RoutingDecision, RoutingPolicy


@dataclass(slots=True)
class BanditRouter:
    """Select policy arms by epsilon-greedy, UCB1, or beta-Bernoulli sampling."""

    arms: tuple[str, ...]
    strategy: str = "ucb1"
    epsilon: float = 0.1
    seed: int = 42
    pulls: dict[str, int] = field(default_factory=dict)
    reward_sums: dict[str, float] = field(default_factory=dict)
    successes: dict[str, float] = field(default_factory=dict)
    failures: dict[str, float] = field(default_factory=dict)
    _random: random.Random = field(init=False, repr=False)
    _total_pulls: int = 0

    def __post_init__(self) -> None:
        """Validate arms and set deterministic priors."""
        if not self.arms or len(set(self.arms)) != len(self.arms):
            raise ValueError("bandit arms must be non-empty and unique")
        if self.strategy not in {"epsilon_greedy", "ucb1", "thompson"}:
            raise ValueError("unsupported bandit strategy")
        if not 0 <= self.epsilon <= 1:
            raise ValueError("epsilon must be between zero and one")
        self._random = random.Random(self.seed)  # noqa: S311 - deterministic strategy sampling
        for arm in self.arms:
            self.pulls.setdefault(arm, 0)
            self.reward_sums.setdefault(arm, 0.0)
            self.successes.setdefault(arm, 1.0)
            self.failures.setdefault(arm, 1.0)

    def choose(self) -> str:
        """Select one policy arm deterministically under the configured seed."""
        untried = [arm for arm in self.arms if self.pulls[arm] == 0]
        if untried:
            return untried[0]
        if self.strategy == "epsilon_greedy" and self._random.random() < self.epsilon:
            return self._random.choice(self.arms)
        if self.strategy == "thompson":
            return max(
                self.arms,
                key=lambda arm: self._random.betavariate(self.successes[arm], self.failures[arm]),
            )
        if self.strategy == "ucb1":
            return max(
                self.arms,
                key=lambda arm: (
                    self.reward_sums[arm] / self.pulls[arm]
                    + math.sqrt(2 * math.log(max(1, self._total_pulls)) / self.pulls[arm])
                ),
            )
        return max(self.arms, key=lambda arm: self.reward_sums[arm] / self.pulls[arm])

    def observe(self, arm: str, reward: float) -> None:
        """Record one bounded reward and update the beta posterior when applicable."""
        if arm not in self.pulls:
            raise ValueError(f"unknown bandit arm: {arm}")
        if not 0 <= reward <= 1:
            raise ValueError("reward must be between zero and one")
        self.pulls[arm] += 1
        self.reward_sums[arm] += reward
        self._total_pulls += 1
        self.successes[arm] += reward
        self.failures[arm] += 1 - reward

    @property
    def regret(self) -> float:
        """Return cumulative pseudo-regret against the best observed mean reward."""
        if not self._total_pulls:
            return 0.0
        best = max(self.reward_sums[arm] / self.pulls[arm] for arm in self.arms if self.pulls[arm])
        return sum(
            self.pulls[arm] * (best - self.reward_sums[arm] / self.pulls[arm])
            for arm in self.arms
            if self.pulls[arm]
        )


@dataclass(slots=True)
class BanditRoutingPolicy:
    """Select among real routing policies and learn from each completed route."""

    name: str
    strategy: str
    delegates: dict[str, RoutingPolicy]
    arms: tuple[str, ...]
    seed: int = 42
    assignments: dict[int, str] = field(default_factory=dict)
    assignment_order: deque[int] = field(default_factory=deque)
    selector: BanditRouter = field(init=False)

    def __post_init__(self) -> None:
        """Create a deterministic selector over the supplied real policies."""
        self.selector = BanditRouter(self.arms, strategy=self.strategy, seed=self.seed)

    def select(
        self,
        candidates: list[BackendSnapshot],
        *,
        request_id: str,
        at: datetime,
        rotation: int,
        weights: dict[str, float],
    ) -> RoutingDecision:
        """Delegate backend choice to the selected arm and annotate its decision."""
        arm = self.selector.choose()
        base = self.delegates[arm].select(
            candidates,
            request_id=request_id,
            at=at,
            rotation=rotation,
            weights=weights,
        )
        decision = RoutingDecision(
            request_id,
            self.name,
            base.chosen_backend_id,
            f"{self.strategy} selected {arm}: {base.reason}",
            base.candidates,
            at,
        )
        key = id(decision)
        self.assignments[key] = arm
        self.assignment_order.append(key)
        while len(self.assignment_order) > 10000:
            expired = self.assignment_order.popleft()
            self.assignments.pop(expired, None)
        return decision

    def observe(self, decision: RoutingDecision, reward: float) -> None:
        """Update the selected policy arm from a bounded routing reward."""
        arm = self.assignments.pop(id(decision), None)
        if arm is not None:
            self.selector.observe(arm, min(1.0, max(0.0, reward)))

    def reset(self) -> None:
        """Clear learned rewards and unfinished assignments for a new run."""
        self.selector = BanditRouter(self.arms, strategy=self.strategy, seed=self.seed)
        self.assignments.clear()
        self.assignment_order.clear()
