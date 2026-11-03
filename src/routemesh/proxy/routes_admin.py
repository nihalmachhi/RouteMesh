"""Backward-compatible import facade for the split operations APIs."""

from routemesh.admin.routes_admin import require_admin, router

__all__ = ["require_admin", "router"]
