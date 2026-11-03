"""Clock interface for deterministic time-dependent tests."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Supplies monotonic and wall-clock time to stateful services."""

    def monotonic(self) -> float: ...

    def utc_now(self) -> datetime: ...


class SystemClock:
    """Production clock backed by the system runtime."""

    def monotonic(self) -> float:
        """Return a monotonic value suitable for durations."""
        import time

        return time.monotonic()

    def utc_now(self) -> datetime:
        """Return timezone-aware UTC wall-clock time."""
        return datetime.now(UTC)
