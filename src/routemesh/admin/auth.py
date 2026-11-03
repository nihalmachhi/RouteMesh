"""Authentication dependency shared by operations endpoints."""

import secrets

from fastapi import Header, HTTPException, Request

from routemesh.core.settings import Settings


async def require_admin(
    request: Request, x_routemesh_admin_token: str | None = Header(default=None)
) -> None:
    """Require a configured admin token for every operations endpoint."""
    settings: Settings = request.app.state.settings
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="admin token is not configured")
    if not secrets.compare_digest(settings.admin_token, x_routemesh_admin_token or ""):
        raise HTTPException(status_code=401, detail="invalid admin token")
