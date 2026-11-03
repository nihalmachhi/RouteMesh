"""Rolling failure-rate ejection for repeatedly failing backend instances."""

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class OutlierDetector:
    """Temporarily eject a backend after a bounded failure window trips."""

    window_size: int = 20
    minimum_requests: int = 5
    failure_threshold: float = 0.6
    ejection_seconds: float = 15.0
    outcomes: deque[bool] = field(default_factory=deque)
    ejected_until: float = 0.0

    def __post_init__(self) -> None:
        """Reject unsafe or nonsensical detector configuration."""
        if self.window_size < 1 or not 1 <= self.minimum_requests <= self.window_size:
            raise ValueError("outlier request window is invalid")
        if not 0 < self.failure_threshold <= 1 or self.ejection_seconds <= 0:
            raise ValueError("outlier threshold and ejection duration must be positive")

    def record(self, succeeded: bool, now: float) -> bool:
        """Add an outcome and return whether this sample triggers ejection."""
        self.outcomes.append(succeeded)
        while len(self.outcomes) > self.window_size:
            self.outcomes.popleft()
        if now < self.ejected_until or len(self.outcomes) < self.minimum_requests:
            return False
        failure_rate = sum(not outcome for outcome in self.outcomes) / len(self.outcomes)
        if failure_rate >= self.failure_threshold:
            self.ejected_until = now + self.ejection_seconds
            return True
        return False

    def is_ejected(self, now: float) -> bool:
        """Check whether the temporary ejection window remains active."""
        return now < self.ejected_until
