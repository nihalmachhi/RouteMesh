"""Validated directed acyclic service graphs and impact calculations."""

from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf


@dataclass(frozen=True, slots=True)
class ServiceEdge:
    """One directed call edge with retry, latency, and locality cost."""

    source: str
    target: str
    retries: int = 0
    timeout_s: float = 1.0
    latency_ms: float = 0.0
    locality_cost: float = 0.0


class ServiceGraph:
    """Represent a service DAG for blast-radius and path planning."""

    def __init__(self, nodes: set[str], edges: list[ServiceEdge]) -> None:
        """Validate node references, edge values, and acyclicity."""
        self.nodes = set(nodes)
        self.edges = tuple(edges)
        self.outgoing: dict[str, list[ServiceEdge]] = {node: [] for node in nodes}
        self.incoming: dict[str, list[ServiceEdge]] = {node: [] for node in nodes}
        for edge in edges:
            if edge.source not in nodes or edge.target not in nodes:
                raise ValueError("service edge references an unknown node")
            if (
                edge.retries < 0
                or edge.timeout_s <= 0
                or edge.latency_ms < 0
                or edge.locality_cost < 0
            ):
                raise ValueError("service edge costs and retry count must be non-negative")
            self.outgoing[edge.source].append(edge)
            self.incoming[edge.target].append(edge)
        self.topological_order = self._topological_order()

    def _topological_order(self) -> tuple[str, ...]:
        """Return a deterministic topological ordering or reject cycles."""
        degree = {node: len(self.incoming[node]) for node in self.nodes}
        ready = sorted(node for node, count in degree.items() if count == 0)
        order = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for edge in sorted(self.outgoing[node], key=lambda item: item.target):
                degree[edge.target] -= 1
                if degree[edge.target] == 0:
                    ready.append(edge.target)
                    ready.sort()
        if len(order) != len(self.nodes):
            raise ValueError("service graph contains a cycle")
        return tuple(order)

    def retry_amplification(self, source: str) -> int:
        """Return the largest product of attempts along a path from a node."""
        self._require_node(source)
        multiplier = {node: 0 for node in self.nodes}
        multiplier[source] = 1
        for node in self.topological_order:
            if multiplier[node] == 0:
                continue
            for edge in self.outgoing[node]:
                multiplier[edge.target] = max(
                    multiplier[edge.target], multiplier[node] * (edge.retries + 1)
                )
        return max(multiplier.values(), default=1)

    def blast_radius(self, failed_node: str) -> tuple[str, ...]:
        """Return the failed service and all upstream callers that depend on it."""
        self._require_node(failed_node)
        found = {failed_node}
        pending = [failed_node]
        while pending:
            node = pending.pop()
            for edge in self.incoming[node]:
                if edge.source not in found:
                    found.add(edge.source)
                    pending.append(edge.source)
        return tuple(sorted(found))

    def critical_path_ms(self, source: str, target: str) -> float:
        """Calculate the longest latency path between two nodes in the DAG."""
        self._require_node(source)
        self._require_node(target)
        distance = {node: -inf for node in self.nodes}
        distance[source] = 0.0
        for node in self.topological_order:
            if distance[node] == -inf:
                continue
            for edge in self.outgoing[node]:
                distance[edge.target] = max(distance[edge.target], distance[node] + edge.latency_ms)
        if distance[target] == -inf:
            raise ValueError("target is unreachable from source")
        return distance[target]

    def min_cost_path(
        self, source: str, target: str, latency_weight: float = 1.0
    ) -> tuple[str, ...]:
        """Use Dijkstra with weighted latency and locality costs."""
        self._require_node(source)
        self._require_node(target)
        if latency_weight < 0:
            raise ValueError("latency weight must be non-negative")
        costs = {node: inf for node in self.nodes}
        previous: dict[str, str] = {}
        costs[source] = 0.0
        queue = [(0.0, source)]
        while queue:
            cost, node = heappop(queue)
            if cost != costs[node]:
                continue
            if node == target:
                break
            for edge in self.outgoing[node]:
                next_cost = cost + latency_weight * edge.latency_ms + edge.locality_cost
                if next_cost < costs[edge.target]:
                    costs[edge.target] = next_cost
                    previous[edge.target] = node
                    heappush(queue, (next_cost, edge.target))
        if costs[target] == inf:
            raise ValueError("target is unreachable from source")
        path = [target]
        while path[-1] != source:
            path.append(previous[path[-1]])
        return tuple(reversed(path))

    def _require_node(self, node: str) -> None:
        """Reject requests for a missing service node."""
        if node not in self.nodes:
            raise ValueError(f"unknown service node: {node}")
