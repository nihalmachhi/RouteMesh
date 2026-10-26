"""Per-backend closed/open/half-open circuit-breaker state machine."""

from collections import deque
from dataclasses import dataclass, field

from routemesh.common.clock import Clock, SystemClock


@dataclass(slots=True)
class CircuitBreaker:
    """Track failures in a bounded window and gate recovery probes."""

    consecutive_limit: int = 5
    window_size: int = 20
    error_rate_limit: float = 0.5
    open_seconds: float = 10.0
    recovery_successes: int = 3
    max_half_open_probes: int = 2
    clock: Clock = field(default_factory=SystemClock)
    state: str = "closed"
    opened_at: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    half_open_in_flight: int = 0
    outcomes: deque[bool] = field(default_factory=deque)

    def can_select(self) -> bool:
        """Check if normal traffic or a recovery probe is eligible."""
        self._refresh_state()
        return self.state == "closed" or (
            self.state == "half_open" and self.half_open_in_flight < self.max_half_open_probes
        )

    def allow_request(self) -> bool:
        """Reserve a bounded half-open probe after checking eligibility."""
        if not self.can_select():
            return False
        if self.state == "half_open":
            self.half_open_in_flight += 1
        return True

    def record(self, succeeded: bool) -> None:
        """Update rolling failures and transition state after an outcome."""
        self.outcomes.append(succeeded)
        while len(self.outcomes) > self.window_size:
            self.outcomes.popleft()
        if self.state == "half_open":
            self.half_open_in_flight = max(0, self.half_open_in_flight - 1)
            if not succeeded:
                self._open()
                return
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.recovery_successes:
                self.state = "closed"
                self.consecutive_failures = 0
                self.consecutive_successes = 0
            return
        self.consecutive_failures = 0 if succeeded else self.consecutive_failures + 1
        failures = sum(not result for result in self.outcomes)
        error_rate = failures / len(self.outcomes)
        if self.consecutive_failures >= self.consecutive_limit or (
            len(self.outcomes) >= self.window_size and error_rate > self.error_rate_limit
        ):
            self._open()

    def _refresh_state(self) -> None:
        """Make an expired open circuit available for bounded recovery probes."""
        if self.state == "open" and self.clock.monotonic() - self.opened_at >= self.open_seconds:
            self.state = "half_open"
            self.half_open_in_flight = 0
            self.consecutive_successes = 0

    def _open(self) -> None:
        """Open the circuit and reset any in-flight probe bookkeeping."""
        self.state = "open"
        self.opened_at = self.clock.monotonic()
        self.half_open_in_flight = 0
        self.consecutive_successes = 0
