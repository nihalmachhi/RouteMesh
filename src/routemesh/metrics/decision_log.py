"""Bounded explainable routing decision history."""

from collections import deque
from dataclasses import asdict
from threading import Lock

from routemesh.policies.base import RoutingDecision


class DecisionLog:
    """Retain recent routing decisions without unbounded memory growth."""

    def __init__(self, capacity: int = 500) -> None:
        self._items: deque[RoutingDecision] = deque(maxlen=capacity)
        self._lock = Lock()

    def append(self, decision: RoutingDecision) -> None:
        """Add one immutable policy decision to the recent history."""
        with self._lock:
            self._items.append(decision)

    def clear(self) -> None:
        """Clear recent entries before an isolated measurement run."""
        with self._lock:
            self._items.clear()

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        """Return newest-first JSON-serializable decisions."""
        with self._lock:
            values = list(self._items)[-max(1, min(limit, 500)) :]
        return [asdict(item) for item in reversed(values)]
