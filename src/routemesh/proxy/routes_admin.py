"""Read-only operations API and guarded demo controls."""

import asyncio
import json
import secrets
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routemesh.common.settings import Settings
from routemesh.metrics.decision_log import DecisionLog
from routemesh.policies.registry import get_policy

router = APIRouter()


class PolicyUpdate(BaseModel):
    """Validate an active routing policy change."""

    policy: str


class BehaviorUpdate(BaseModel):
    """Bounded test-backend behavior control."""

    latency_ms: float = Field(default=0, ge=0, le=10_000)
    jitter_ms: float = Field(default=0, ge=0, le=5_000)
    error_rate: float = Field(default=0, ge=0, le=1)
    cpu_percent: float = Field(default=10, ge=0, le=100)
    down: bool = False


async def require_admin(
    request: Request, x_routemesh_admin_token: str | None = Header(default=None)
) -> None:
    """Require the configured token on every state-changing admin endpoint."""
    settings: Settings = request.app.state.settings
    if not secrets.compare_digest(settings.admin_token or "", x_routemesh_admin_token or ""):
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/admin/backends")
async def list_backends(request: Request) -> list[dict[str, object]]:
    """Expose backend health and live routing measurements."""
    result = []
    for item in await request.app.state.registry.snapshots():
        result.append(
            {
                "id": item.backend_id,
                "url": item.url,
                "health_state": "HEALTHY" if item.healthy else "UNHEALTHY",
                "circuit_state": request.app.state.router.breakers[item.backend_id].state,
                "in_flight": item.in_flight,
                "routed_requests": request.app.state.router.request_counts[item.backend_id],
                "ewma_latency_ms": item.ewma_latency_ms,
                "error_rate": item.error_rate,
                "cpu_percent": item.cpu_percent,
                "last_check_at": item.last_check_at.isoformat() if item.last_check_at else None,
            }
        )
    return result


@router.get("/admin/policy")
async def get_active_policy(request: Request) -> dict[str, str]:
    """Return the active policy name."""
    name, _ = await request.app.state.router.policy.current()
    return {"policy": name}


@router.put("/admin/policy", dependencies=[Depends(require_admin)])
async def set_active_policy(body: PolicyUpdate, request: Request) -> dict[str, str]:
    """Switch policy at runtime after validating the registry name."""
    get_policy(body.policy)
    await request.app.state.router.policy.select(body.policy)
    return {"policy": body.policy}


@router.post("/admin/reset", dependencies=[Depends(require_admin)])
async def reset_observations(request: Request) -> dict[str, str]:
    """Reset local counters and breaker history for an isolated benchmark run."""
    await request.app.state.router.reset_observations()
    return {"status": "reset"}


@router.get("/admin/decisions")
async def recent_decisions(request: Request, limit: int = 100) -> list[dict[str, object]]:
    """Return bounded, newest-first decisions and candidate scores."""
    decisions: DecisionLog = request.app.state.decisions
    return decisions.recent(limit)


@router.get("/admin/stream")
async def event_stream(request: Request) -> StreamingResponse:
    """Stream best-effort JSON events over Server-Sent Events."""

    async def events() -> AsyncIterator[str]:
        async with request.app.state.events.subscribe() as queue:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    yield "data: " + json.dumps(item, separators=(",", ":")) + "\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post(
    "/admin/backends/{backend_id}/behavior",
    dependencies=[Depends(require_admin)],
)
async def set_backend_behavior(
    backend_id: str, body: BehaviorUpdate, request: Request
) -> dict[str, object]:
    """Send a demo behavior change to a configured test backend."""
    snapshots = await request.app.state.registry.snapshots()
    backend = next((item for item in snapshots if item.backend_id == backend_id), None)
    if backend is None:
        raise HTTPException(status_code=404, detail="unknown backend")
    response = await request.app.state.http_client.post(
        f"{backend.url}/admin/behavior", json=body.model_dump()
    )
    response.raise_for_status()
    return {"backend_id": backend_id, "behavior": response.json()}
