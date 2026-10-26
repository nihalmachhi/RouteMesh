"""Backend selection, forwarding, telemetry updates, and safe retries."""

import asyncio
import logging
import math

import httpx
from fastapi import Request, Response

from routemesh.common.clock import Clock, SystemClock
from routemesh.common.errors import NoHealthyBackend
from routemesh.discovery.config_loader import RouteConfig
from routemesh.discovery.registry import BackendRegistry
from routemesh.health.circuit_breaker import CircuitBreaker
from routemesh.metrics.decision_log import DecisionLog
from routemesh.metrics.event_stream import EventStream
from routemesh.metrics.ewma import Ewma
from routemesh.metrics.prometheus import ProxyMetrics
from routemesh.metrics.rolling_window import RollingWindow
from routemesh.policies.base import RoutingDecision
from routemesh.policies.registry import create_policies, get_policy
from routemesh.policies.thompson_sampling import ThompsonSamplingPolicy
from routemesh.proxy.forwarder import HttpForwarder

logger = logging.getLogger(__name__)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


class RetryBudget:
    """Cap retries to a configured fraction of original requests."""

    def __init__(self, ratio: float) -> None:
        self._ratio = max(0.0, ratio)
        self._earned = 0.0
        self._spent = 0

    def start_request(self) -> None:
        """Earn a fractional retry token for each original request."""
        self._earned += self._ratio

    def consume(self) -> bool:
        """Spend a retry token if the global budget permits it."""
        if self._spent >= math.floor(self._earned):
            return False
        self._spent += 1
        return True


class PolicyState:
    """Hold the active policy name and deterministic rotation counter."""

    def __init__(self, name: str) -> None:
        get_policy(name)
        self.name = name
        self.policies = create_policies()
        self.rotation = 0
        self.lock = asyncio.Lock()

    async def current(self) -> tuple[str, int]:
        """Read policy and rotation atomically."""
        async with self.lock:
            return self.name, self.rotation

    async def select(self, name: str) -> None:
        """Change policy only to a registered strategy."""
        get_policy(name)
        async with self.lock:
            self.name = name

    async def advance(self) -> None:
        """Advance the round-robin tie rotation."""
        async with self.lock:
            self.rotation += 1

    async def reset(self) -> None:
        """Reset deterministic policy rotation between benchmark samples."""
        async with self.lock:
            self.rotation = 0
            self.policies = create_policies()


class ProxyRouter:
    """Choose eligible backends, record explainable decisions, and forward."""

    def __init__(
        self,
        registry: BackendRegistry,
        forwarder: HttpForwarder,
        config: RouteConfig,
        metrics: ProxyMetrics,
        decisions: DecisionLog,
        events: EventStream,
        clock: Clock | None = None,
    ) -> None:
        self.registry = registry
        self.forwarder = forwarder
        self.config = config
        self.metrics = metrics
        self.decisions = decisions
        self.events = events
        self.clock = clock or SystemClock()
        self.policy = PolicyState(config.policy)
        self.breakers = {
            backend.id: CircuitBreaker(
                int(config.circuit_breaker["consecutive_failures"]),
                int(config.circuit_breaker["window"]),
                float(config.circuit_breaker["error_rate"]),
                float(config.circuit_breaker["open_s"]),
                int(config.health["recovery_successes"]),
                clock=self.clock,
            )
            for backend in config.backends
        }
        self.latencies = {
            backend_id: Ewma(float(config.scoring["ewma_alpha"])) for backend_id in self.breakers
        }
        self.windows = {
            backend_id: RollingWindow(int(config.circuit_breaker["window"]))
            for backend_id in self.breakers
        }
        self.retry_budget = RetryBudget(float(config.retries["budget_ratio"]))
        self.request_counts = {backend_id: 0 for backend_id in self.breakers}

    async def reset_observations(self) -> None:
        """Reset policy telemetry and breaker state before a controlled run."""
        self.breakers = {
            backend.id: CircuitBreaker(
                int(self.config.circuit_breaker["consecutive_failures"]),
                int(self.config.circuit_breaker["window"]),
                float(self.config.circuit_breaker["error_rate"]),
                float(self.config.circuit_breaker["open_s"]),
                int(self.config.health["recovery_successes"]),
                clock=self.clock,
            )
            for backend in self.config.backends
        }
        self.latencies = {
            backend_id: Ewma(float(self.config.scoring["ewma_alpha"]))
            for backend_id in self.breakers
        }
        self.windows = {
            backend_id: RollingWindow(int(self.config.circuit_breaker["window"]))
            for backend_id in self.breakers
        }
        self.request_counts = {backend_id: 0 for backend_id in self.breakers}
        await self.policy.reset()
        self.decisions.clear()
        for metric in (
            self.metrics.requests,
            self.metrics.duration,
            self.metrics.in_flight,
            self.metrics.decisions,
        ):
            metric.clear()
        self.events.publish({"type": "benchmark.reset"})

    async def choose(
        self, request: Request, path: str, request_id: str, excluded: set[str]
    ) -> tuple[RoutingDecision, str]:
        """Filter unhealthy/open backends then invoke the configured pure policy."""
        snapshots = await self.registry.snapshots()
        available = []
        for item in snapshots:
            breaker = self.breakers[item.backend_id]
            item.circuit_state = breaker.state
            if item.backend_id not in excluded and item.healthy and breaker.can_select():
                available.append(item)
        if not available:
            raise NoHealthyBackend("no healthy backend is currently eligible")
        policy_name, rotation = await self.policy.current()
        decision = self.policy.policies[policy_name].select(
            available,
            request_id=request_id,
            at=self.clock.utc_now(),
            rotation=rotation,
            weights=self.config.scoring,
            context=self._request_context(request, path),
        )
        breaker = self.breakers[decision.chosen_backend_id]
        if not breaker.allow_request():
            return await self.choose(
                request, path, request_id, excluded | {decision.chosen_backend_id}
            )
        await self.policy.advance()
        self.decisions.append(decision)
        self.request_counts[decision.chosen_backend_id] += 1
        self.metrics.decisions.labels(decision.chosen_backend_id, policy_name).inc()
        self.events.publish(
            {
                "type": "routing.decision",
                "request_id": request_id,
                "policy": policy_name,
                "backend_id": decision.chosen_backend_id,
            }
        )
        logger.info(
            "routing decision",
            extra={
                "request_id": request_id,
                "backend_id": decision.chosen_backend_id,
                "policy": policy_name,
                "event": "route_selected",
            },
        )
        backend_url = next(
            item.url for item in snapshots if item.backend_id == decision.chosen_backend_id
        )
        return decision, backend_url

    async def forward(self, request: Request, path: str, request_id: str) -> Response:
        """Forward once, retry only safe/idempotency-key requests under budget."""
        retry_allowed = request.method in SAFE_METHODS or "idempotency-key" in request.headers
        self.retry_budget.start_request()
        maximum = int(self.config.retries["max_attempts"])
        excluded: set[str] = set()
        last_error: httpx.HTTPError | None = None
        for attempt in range(maximum):
            decision: RoutingDecision | None = None
            attempt_started = self.clock.monotonic()
            try:
                decision, backend_url = await self.choose(request, path, request_id, excluded)
                response, elapsed = await self._forward_once(
                    request, path, request_id, decision, backend_url
                )
                failed = response.status_code >= 500
                await self._record(decision, response.status_code, elapsed, failed)
                if not failed or not retry_allowed or attempt + 1 >= maximum:
                    return response
                if not self.retry_budget.consume():
                    return response
                excluded.add(decision.chosen_backend_id)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if decision is not None:
                    status_code = 504 if isinstance(exc, httpx.TimeoutException) else 502
                    await self._record(
                        decision, status_code, self.clock.monotonic() - attempt_started, True
                    )
                if not retry_allowed or attempt + 1 >= maximum or not self.retry_budget.consume():
                    break
                if decision is not None:
                    excluded.add(decision.chosen_backend_id)
        if last_error is not None:
            raise last_error
        raise NoHealthyBackend("no backend returned a usable response")

    @staticmethod
    def _request_context(request: Request, path: str) -> dict[str, str]:
        """Map arbitrary paths and sizes into bounded contextual bandit features."""
        first_segment = path.strip("/").split("/", maxsplit=1)[0].lower()
        path_class = first_segment if first_segment in {"api", "static", "health"} else "other"
        try:
            size = int(request.headers.get("content-length", "0"))
        except ValueError:
            size = 0
        size_class = "large" if size >= 1_000_000 else "medium" if size >= 16_384 else "small"
        return {"path_class": path_class, "size_class": size_class}

    async def _forward_once(
        self,
        request: Request,
        path: str,
        request_id: str,
        decision: RoutingDecision,
        backend_url: str,
    ) -> tuple[Response, float]:
        """Measure one outbound request and atomically update its in-flight gauge."""
        backend_id = decision.chosen_backend_id
        await self.registry.adjust_in_flight(backend_id, 1)
        self.metrics.in_flight.labels(backend_id).inc()
        started = self.clock.monotonic()
        try:
            response = await self.forwarder.send(request, backend_url, path, request_id)
            return response, self.clock.monotonic() - started
        finally:
            await self.registry.adjust_in_flight(backend_id, -1)
            self.metrics.in_flight.labels(backend_id).dec()

    async def _record(
        self, decision: RoutingDecision, status_code: int, elapsed: float, failed: bool
    ) -> None:
        """Update latency, error window, breaker, and request metrics."""
        backend_id = decision.chosen_backend_id
        policy = self.policy.policies[decision.policy]
        if decision.context is not None and isinstance(policy, ThompsonSamplingPolicy):
            policy.observe(
                decision.context,
                backend_id,
                elapsed * 1000,
                failed,
                self.config.scoring,
            )
        latency = self.latencies[backend_id].update(elapsed * 1000)
        error_rate = self.windows[backend_id].add(not failed)
        self.breakers[backend_id].record(not failed)
        await self.registry.update_runtime(
            backend_id,
            ewma_latency_ms=latency,
            error_rate=error_rate,
            circuit_state=self.breakers[backend_id].state,
        )
        self.metrics.duration.labels(backend_id, decision.policy).observe(elapsed)
        self.metrics.requests.labels(
            backend_id, decision.policy, self.metrics.status_class(status_code)
        ).inc()
