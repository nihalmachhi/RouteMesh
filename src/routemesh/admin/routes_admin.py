"""Aggregate the split operations API routers."""

from fastapi import APIRouter

from routemesh.admin.auth import require_admin
from routemesh.admin.control import router as control_router
from routemesh.admin.demo_faults import router as demo_fault_router
from routemesh.admin.read import router as read_router

router = APIRouter()
router.include_router(read_router)
router.include_router(control_router)
router.include_router(demo_fault_router)

__all__ = ["require_admin", "router"]
