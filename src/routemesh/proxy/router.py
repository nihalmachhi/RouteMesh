"""Backend selection, forwarding, telemetry updates, and safe retries."""

import asyncio
import logging
from collections import deque
from collections.abc import AsyncIterator

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from routemesh.core.clock import Clock, SystemClock
from routemesh.core.errors import NoHealthyBackend
from routemesh.discovery.config_loader import RouteConfig
from routemesh.discovery.registry import BackendRegistry
from routemesh.health.circuit_breaker import CircuitBreaker
from routemesh.health.outlier import OutlierDetector
from routemesh.metrics.decision_log import DecisionLog
from routemesh.metrics.event_stream import EventStream
from routemesh.metrics.ewma import Ewma
from routemesh.metrics.prometheus import ProxyMetrics
from routemesh.metrics.rolling_window import RollingWindow
from routemesh.policies.bandit import BanditRoutingPolicy
from routemesh.policies.base import RoutingDecision, RoutingPolicy
from routemesh.policies.registry import create_policy_registry, get_policy
from routemesh.proxy.forwarder import HttpForwarder
from routemesh.resilience.adaptive_limit import AdaptiveConcurrencyLimit

logger = logging.getLogger(__name__)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


class RetryBudget:
    """Cap retries to a configured fraction of original requests."""

    def __init__(
        self, ratio: float, clock: Clock | None = None, token_ttl_seconds: float = 10.0
    ) -> None:
        self._ratio = max(0.0, ratio)
        self._capacity = max(1.0, self._ratio * 100)
        self._clock = clock or SystemClock()
        self._token_ttl_seconds = token_ttl_seconds
        self._earned: deque[tuple[float, float]] = deque()

    def start_request(self) -> None:
        """Earn a fractional retry token, capped to a finite burst allowance."""
        now = self._clock.monotonic()
        self._expire(now)
        earned = sum(amount for _, amount in self._earned)
        if self._ratio > 0:
            credit = min(self._ratio, self._capacity - earned)
            if credit > 0:
                self._earned.append((now, credit))

    def consume(self) -> bool:
        """Spend one retry token if the global budget permits it."""
        now = self._clock.monotonic()
        self._expire(now)
        earned = sum(amount for _, amount in self._earned)
        if earned < 1.0 - 1e-9:
            return False
        remaining = 1.0
        while remaining > 1e-9:
            timestamp, credit = self._earned.popleft()
            spent = min(credit, remaining)
            remaining -= spent
            if credit - spent > 1e-9:
                self._earned.appendleft((timestamp, credit - spent))
        return True

    def reset(self) -> None:
        """Discard accumulated retry allowance between controlled runs."""
        self._earned.clear()

    def _expire(self, now: float) -> None:
        """Discard unused credits and spends outside the rolling time window."""
        cutoff = now - self._token_ttl_seconds
        while self._earned and self._earned[0][0] <= cutoff:
            self._earned.popleft()


class PolicyState:
    """Hold the active policy name and deterministic rotation counter."""

    def __init__(self, name: str, policies: dict[str, RoutingPolicy] | None = None) -> None:
        self.policies = policies or create_policy_registry()
        if name not in self.policies:
            get_policy(name)
        self.name = name
        self.rotation = 0
        self.lock = asyncio.Lock()

    async def current(self) -> tuple[str, int]:
        """Read policy and rotation atomically."""
        async with self.lock:
            return self.name, self.rotation

    async def select(self, name: str) -> None:
        """Change policy only to a registered strategy."""
        if name not in self.policies:
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
        self.policies = create_policy_registry()
        self.policy = PolicyState(config.policy, self.policies)
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
        self.retry_budget = RetryBudget(float(config.retries["budget_ratio"]), clock=self.clock)
        self.request_counts = {backend_id: 0 for backend_id in self.breakers}
        per_backend_limit = int(config.backpressure.get("per_backend", 100))
        self.adaptive_limits = {
            backend_id: AdaptiveConcurrencyLimit(
                minimum=1, maximum=per_backend_limit, initial=per_backend_limit
            )
            for backend_id in self.breakers
        }
        self.outliers = {backend_id: OutlierDetector() for backend_id in self.breakers}

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
        self.outliers = {backend_id: OutlierDetector() for backend_id in self.breakers}
        for adaptive_limit in self.adaptive_limits.values():
            await adaptive_limit.reset()
        self.request_counts = {backend_id: 0 for backend_id in self.breakers}
        self.retry_budget.reset()
        await self.policy.reset()
        self.decisions.clear()
        for policy in self.policies.values():
            if isinstance(policy, BanditRoutingPolicy):
                policy.reset()
        self.events.publish({"type": "benchmark.reset"})

    async def choose(self, request_id: str, excluded: set[str]) -> tuple[RoutingDecision, str]:
        """Filter unhealthy/open backends then invoke the configured pure policy."""
        snapshots = await self.registry.snapshots()
        available = []
        for item in snapshots:
            breaker = self.breakers[item.backend_id]
            item.circuit_state = breaker.state
            if (
                item.backend_id not in excluded
                and item.healthy
                and breaker.can_select()
                and not self.outliers[item.backend_id].is_ejected(self.clock.monotonic())
            ):
                available.append(item)
        if not available:
            raise NoHealthyBackend("no healthy backend is currently eligible")
        policy_name, rotation = await self.policy.current()
        decision = self.policies[policy_name].select(
            available,
            request_id=request_id,
            at=self.clock.utc_now(),
            rotation=rotation,
            weights=self.config.scoring,
        )
        breaker = self.breakers[decision.chosen_backend_id]
        if not breaker.allow_request():
            return await self.choose(request_id, excluded | {decision.chosen_backend_id})
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
        content_length = request.headers.get("content-length", "0")
        body_replayable = content_length == "0" and "transfer-encoding" not in request.headers
        retry_allowed = (request.method in SAFE_METHODS and body_replayable) or (
            "idempotency-key" in request.headers and body_replayable
        )
        self.retry_budget.start_request()
        if (
            bool(getattr(self.config, "hedging", {}).get("enabled", False))
            and int(self.config.retries["max_attempts"]) > 1
            and request.method in {"GET", "HEAD"}
            and body_replayable
        ):
            return await self._forward_hedged(request, path, request_id)
        maximum = int(self.config.retries["max_attempts"])
        excluded: set[str] = set()
        last_error: httpx.HTTPError | None = None
        last_response: Response | None = None
        for attempt in range(maximum):
            decision: RoutingDecision | None = None
            attempt_started = self.clock.monotonic()
            try:
                decision, backend_url = await self.choose(request_id, excluded)
                response, elapsed = await self._forward_once(
                    request, path, request_id, decision, backend_url
                )
                last_response = response
                failed = response.status_code >= 500
                await self._record(decision, response.status_code, elapsed, failed)
                if not failed or not retry_allowed or attempt + 1 >= maximum:
                    return response
                if not self.retry_budget.consume():
                    return response
                background = getattr(response, "background", None)
                if background is not None:
                    await background()
                excluded.add(decision.chosen_backend_id)
            except NoHealthyBackend:
                if last_response is not None:
                    return last_response
                raise
            except httpx.HTTPError as exc:
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
            finally:
                if decision is not None:
                    self.breakers[decision.chosen_backend_id].release_probe()
        if last_response is not None:
            return last_response
        if last_error is not None:
            raise last_error
        raise NoHealthyBackend("no backend returned a usable response")

    async def _forward_hedged(self, request: Request, path: str, request_id: str) -> Response:
        """Hedge one safe request after a delay, bounded by retry credits."""
        primary, primary_url = await self.choose(request_id, set())
        tasks: dict[str, asyncio.Task[tuple[Response, float]]] = {
            "primary": asyncio.create_task(
                self._forward_once(request, path, request_id, primary, primary_url)
            )
        }
        decisions = {"primary": primary}
        attempt_started = {"primary": self.clock.monotonic()}
        finished: set[str] = set()
        winner: Response | None = None
        last_response: Response | None = None
        last_error: httpx.HTTPError | None = None

        async def finish(task_name: str) -> tuple[Response, float] | None:
            nonlocal last_response, last_error
            try:
                response, elapsed = await tasks[task_name]
            except httpx.HTTPError as exc:
                last_error = exc
                decision = decisions[task_name]
                status_code = 504 if isinstance(exc, httpx.TimeoutException) else 502
                await self._record(
                    decision,
                    status_code,
                    self.clock.monotonic() - attempt_started[task_name],
                    True,
                )
                finished.add(task_name)
                return None
            decision = decisions[task_name]
            failed = response.status_code >= 500
            await self._record(decision, response.status_code, elapsed, failed)
            if failed:
                if last_response is not None:
                    await discard(last_response)
                last_response = response
            finished.add(task_name)
            return response, elapsed

        async def discard(response: Response) -> None:
            iterator = getattr(response, "body_iterator", None)
            close = getattr(iterator, "aclose", None)
            if close is not None:
                await close()
            if response.background is not None:
                await response.background()

        async def cleanup() -> None:
            nonlocal winner
            pending = [task for task in tasks.values() if not task.done()]
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in tasks.values():
                if task.cancelled() or task.exception() is not None:
                    continue
                response, _ = task.result()
                if response is not winner:
                    await discard(response)
            for decision in decisions.values():
                self.breakers[decision.chosen_backend_id].release_probe()

        try:
            delay = float(self.config.hedging["delay_ms"]) / 1000
            done, _ = await asyncio.wait({tasks["primary"]}, timeout=delay)
            primary_finished = False
            if done:
                primary_finished = True
                result = await finish("primary")
                if result is not None and result[0].status_code < 500:
                    winner = result[0]
                    return winner
            if not self.retry_budget.consume():
                if not primary_finished:
                    result = await finish("primary")
                    if result is not None:
                        winner = result[0]
                        return winner
                if last_response is not None:
                    winner = last_response
                    return last_response
                raise last_error or httpx.HTTPError("primary hedge attempt failed")
            secondary, secondary_url = await self.choose(request_id, {primary.chosen_backend_id})
            decisions["secondary"] = secondary
            attempt_started["secondary"] = self.clock.monotonic()
            tasks["secondary"] = asyncio.create_task(
                self._forward_once(request, path, request_id, secondary, secondary_url)
            )
            pending_names = {"secondary"} if primary_finished else {"primary", "secondary"}
            while pending_names:
                pending_tasks = {tasks[name] for name in pending_names}
                completed, _ = await asyncio.wait(
                    pending_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task_name in ("primary", "secondary"):
                    if task_name not in pending_names or tasks[task_name] not in completed:
                        continue
                    pending_names.remove(task_name)
                    if task_name in finished:
                        continue
                    result = await finish(task_name)
                    if result is None:
                        continue
                    response, _ = result
                    if response.status_code < 500:
                        if last_response is not None:
                            await discard(last_response)
                            last_response = None
                        winner = response
                        return response
            if last_response is not None:
                winner = last_response
                return last_response
            raise last_error or httpx.HTTPError("both hedge attempts failed")
        except NoHealthyBackend:
            if last_response is not None:
                winner = last_response
                return winner
            if "primary" not in finished:
                result = await finish("primary")
                if result is not None:
                    winner = result[0]
                    return winner
            if last_error is not None:
                raise last_error from None
            raise NoHealthyBackend("no alternate backend for hedge") from None
        finally:
            await cleanup()

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
        adaptive_limit = self.adaptive_limits[backend_id]
        await adaptive_limit.acquire()
        await self.registry.adjust_in_flight(backend_id, 1)
        self.metrics.in_flight.labels(backend_id).inc()
        released = False

        async def release() -> None:
            nonlocal released
            if not released:
                released = True
                await self.registry.adjust_in_flight(backend_id, -1)
                self.metrics.in_flight.labels(backend_id).dec()
                await adaptive_limit.release()

        started = self.clock.monotonic()
        try:
            response = await self.forwarder.send(request, backend_url, path, request_id)
            elapsed = self.clock.monotonic() - started
            if isinstance(response, StreamingResponse):
                original_iterator = response.body_iterator

                async def tracked_body() -> AsyncIterator[bytes | str | memoryview]:
                    try:
                        async for chunk in original_iterator:
                            yield chunk
                    finally:
                        await release()

                response.body_iterator = tracked_body()
            else:
                await release()
            return response, elapsed
        except BaseException:
            await release()
            raise

    async def _record(
        self, decision: RoutingDecision, status_code: int, elapsed: float, failed: bool
    ) -> None:
        """Update latency, error window, breaker, and request metrics."""
        backend_id = decision.chosen_backend_id
        latency = self.latencies[backend_id].update(elapsed * 1000)
        updated_at = self.clock.utc_now()
        error_rate = self.windows[backend_id].add(not failed)
        self.breakers[backend_id].record(not failed)
        self.outliers[backend_id].record(not failed, self.clock.monotonic())
        await self.adaptive_limits[backend_id].observe(elapsed * 1000, not failed)
        policy = self.policies[decision.policy]
        if isinstance(policy, BanditRoutingPolicy):
            reward = (1.0 if not failed else 0.0) * max(0.0, 1.0 - elapsed)
            policy.observe(decision, reward)
        await self.registry.update_runtime(
            backend_id,
            ewma_latency_ms=latency,
            latency_updated_at=updated_at,
            error_rate=error_rate,
            circuit_state=self.breakers[backend_id].state,
        )
        self.metrics.duration.labels(backend_id, decision.policy).observe(elapsed)
        self.metrics.requests.labels(
            backend_id, decision.policy, self.metrics.status_class(status_code)
        ).inc()
