"""Separate operations-plane ASGI application and listener."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from routemesh.admin.auth import require_admin
from routemesh.admin.routes_admin import router
from routemesh.core.settings import Settings
from routemesh.metrics.prometheus import ProxyMetrics


def create_admin_app(settings: Settings, metrics: ProxyMetrics) -> FastAPI:
    """Create a protected admin app that shares runtime objects with the proxy."""
    app = FastAPI(title="RouteMesh operations", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.dashboard_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-RouteMesh-Admin-Token"],
    )
    app.state.settings = settings
    app.state.metrics = metrics
    app.include_router(router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        """Report liveness on the operations-only listener."""
        return {"status": "ok"}

    @app.get("/metrics", dependencies=[Depends(require_admin)], include_in_schema=False)
    async def metrics_endpoint() -> PlainTextResponse:
        """Expose low-cardinality metrics on the operations-only listener."""
        return PlainTextResponse(
            metrics.content().decode("utf-8"),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return app
