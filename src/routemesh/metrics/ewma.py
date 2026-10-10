"""Exponentially weighted moving average."""

from dataclasses import dataclass


@dataclass(slots=True)
class Ewma:
    """Smooth noisy latency measurements with configurable alpha."""

    alpha: float = 0.2
    value: float | None = None

    def __post_init__(self) -> None:
        """Reject invalid smoothing factors early."""
        if not 0 < self.alpha <= 1:
            raise ValueError("EWMA alpha must be within (0, 1]")

    def update(self, sample: float) -> float:
        """Record a non-negative sample and return the new average."""
        if sample < 0:
            raise ValueError("EWMA samples cannot be negative")
        self.value = (
            sample if self.value is None else (self.alpha * sample + (1 - self.alpha) * self.value)
        )
        return self.value
