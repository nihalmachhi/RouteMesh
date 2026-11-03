"""Authenticated controls for configured demo backends only."""

from fastapi import APIRouter, Depends, HTTPException, Request

from routemesh.admin.auth import require_admin
from routemesh.admin.schemas import BehaviorUpdate

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/admin/backends/{backend_id}/behavior")
async def set_backend_behavior(
    backend_id: str, body: BehaviorUpdate, request: Request
) -> dict[str, object]:
    """Send a bounded behavior change to a backend from the validated registry."""
    snapshots = await request.app.state.registry.snapshots()
    backend = next((item for item in snapshots if item.backend_id == backend_id), None)
    if backend is None:
        raise HTTPException(status_code=404, detail="unknown backend")
    response = await request.app.state.http_client.post(
        f"{backend.url}/admin/behavior", json=body.model_dump()
    )
    response.raise_for_status()
    return {"backend_id": backend_id, "behavior": response.json()}
