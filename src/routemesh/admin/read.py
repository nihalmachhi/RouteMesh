"""Read-only operational state and event stream."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from routemesh.admin.auth import require_admin
from routemesh.metrics.decision_log import DecisionLog

router = APIRouter(dependencies=[Depends(require_admin)])


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
                "backend_reported_in_flight": item.backend_reported_in_flight,
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
