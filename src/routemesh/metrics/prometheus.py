"""Low-cardinality Prometheus instrumentation for proxy traffic."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class ProxyMetrics:
    """Own a private registry so test app instances do not collide."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "routemesh_requests_total",
            "Proxy requests",
            ["backend", "policy", "status_class"],
            registry=self.registry,
        )
        self.duration = Histogram(
            "routemesh_request_duration_seconds",
            "Proxy request latency",
            ["backend", "policy"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
            registry=self.registry,
        )
        self.in_flight = Gauge(
            "routemesh_backend_in_flight",
            "Requests currently forwarded",
            ["backend"],
            registry=self.registry,
        )
        self.decisions = Counter(
            "routemesh_routing_decisions_total",
            "Policy selections by backend",
            ["backend", "policy"],
            registry=self.registry,
        )

    def content(self) -> bytes:
        """Return Prometheus exposition text for the /metrics endpoint."""
        return generate_latest(self.registry)

    @staticmethod
    def status_class(status_code: int) -> str:
        """Reduce status codes to a fixed-cardinality class label."""
        return f"{status_code // 100}xx"
