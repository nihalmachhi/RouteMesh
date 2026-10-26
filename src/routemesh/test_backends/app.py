"""Test backend factory with controllable latency, errors, and health."""

import asyncio
import os
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field

from routemesh.test_backends.behavior import BehaviorState


class BehaviorRequest(BaseModel):
    """Validate demo controls before they reach backend state."""

    latency_ms: float = Field(default=0, ge=0, le=10_000)
    jitter_ms: float = Field(default=0, ge=0, le=5_000)
    error_rate: float = Field(default=0, ge=0, le=1)
    cpu_percent: float = Field(default=10, ge=0, le=100)
    down: bool = False
    flap_every: int = Field(default=0, ge=0, le=100_000)


def create_backend_app(backend_id: str | None = None) -> FastAPI:
    """Build one backend process for local routing and failure experiments."""
    name: str = backend_id or os.getenv("ROUTEMESH_BACKEND_ID") or "backend-a"
    state = BehaviorState()
    randomizer = random.Random(42)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Expose isolated backend state during its process lifetime."""
        app.state.backend_id = name
        app.state.behavior = state
        app.state.randomizer = randomizer
        yield

    app = FastAPI(title=f"RouteMesh {name}", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str | float | int]:
        """Report backend health and the CPU/in-flight telemetry fields."""
        behavior = await state.snapshot()
        return {
            "status": "down" if behavior.down else "ok",
            "cpu_percent": behavior.cpu_percent,
            "in_flight": behavior.in_flight,
        }

    @app.post("/admin/behavior")
    async def update_behavior(body: BehaviorRequest) -> dict[str, float | bool]:
        """Set latency, error, simulated CPU, and down controls."""
        current = await state.update(body.model_dump())
        return {
            "latency_ms": current.latency_ms,
            "jitter_ms": current.jitter_ms,
            "error_rate": current.error_rate,
            "cpu_percent": current.cpu_percent,
            "down": current.down,
            "flap_every": current.flap_every,
        }

    @app.get("/admin/behavior")
    async def get_behavior() -> dict[str, float | bool | int]:
        """Return the current behavior so controlled benchmarks can restore it."""
        current = await state.snapshot()
        return {
            "latency_ms": current.latency_ms,
            "jitter_ms": current.jitter_ms,
            "error_rate": current.error_rate,
            "cpu_percent": current.cpu_percent,
            "down": current.down,
            "flap_every": current.flap_every,
        }

    @app.api_route(
        "/{path:path}",
        methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def handle(request: Request, path: str) -> Response:
        """Apply configured demo behavior and echo a safe response envelope."""
        behavior, flapping_failure = await state.begin_request()
        async with state.lock:
            state.value.in_flight += 1
        try:
            if behavior.down:
                return Response("backend is administratively down", status_code=503)
            delay_ms = behavior.latency_ms + randomizer.uniform(0, behavior.jitter_ms)
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
            if flapping_failure or randomizer.random() < behavior.error_rate:
                return Response("simulated backend error", status_code=503)
            body = await request.body()
            return Response(
                content=body or f"{name} handled /{path}".encode(),
                status_code=200,
                headers={"X-Backend-ID": name, "X-Simulated-CPU": str(behavior.cpu_percent)},
            )
        finally:
            async with state.lock:
                state.value.in_flight = max(0, state.value.in_flight - 1)

    return app


app = create_backend_app()
