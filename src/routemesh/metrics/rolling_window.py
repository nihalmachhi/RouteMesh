"""Bounded recent request outcome window."""

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class RollingWindow:
    """Calculate recent error rate from a bounded outcome history."""

    capacity: int = 20
    outcomes: deque[bool] = field(default_factory=deque)

    def __post_init__(self) -> None:
        """Require a positive observation window."""
        if self.capacity < 1:
            raise ValueError("rolling window capacity must be positive")

    def add(self, succeeded: bool) -> float:
        """Add one outcome and return the resulting error rate."""
        self.outcomes.append(succeeded)
        while len(self.outcomes) > self.capacity:
            self.outcomes.popleft()
        return self.error_rate

    @property
    def error_rate(self) -> float:
        """Return the fraction of failures currently in the window."""
        return (
            0.0
            if not self.outcomes
            else sum(not item for item in self.outcomes) / len(self.outcomes)
        )
