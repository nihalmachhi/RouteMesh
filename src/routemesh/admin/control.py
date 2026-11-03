"""Authenticated policy and observation controls."""

from fastapi import APIRouter, Depends, Request

from routemesh.admin.auth import require_admin
from routemesh.admin.schemas import PolicyUpdate
from routemesh.policies.registry import get_policy

router = APIRouter(dependencies=[Depends(require_admin)])


@router.put("/admin/policy")
async def set_active_policy(body: PolicyUpdate, request: Request) -> dict[str, str]:
    """Switch policy at runtime after validating the registry name."""
    get_policy(body.policy)
    await request.app.state.router.policy.select(body.policy)
    return {"policy": body.policy}


@router.post("/admin/reset")
async def reset_observations(request: Request) -> dict[str, str]:
    """Reset local counters and breaker history before an isolated run."""
    await request.app.state.router.reset_observations()
    return {"status": "reset"}
