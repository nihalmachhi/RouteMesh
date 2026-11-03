"""RouteMesh FastAPI app factory, shared client lifecycle, and API wiring."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from routemesh.admin.app import create_admin_app
from routemesh.core.errors import ConfigurationError
from routemesh.core.logging import configure_logging
from routemesh.core.settings import Settings, get_settings
from routemesh.discovery.config_loader import load_config
from routemesh.discovery.registry import BackendRegistry
from routemesh.health.checker import HealthChecker
from routemesh.metrics.decision_log import DecisionLog
from routemesh.metrics.event_stream import EventStream
from routemesh.metrics.prometheus import ProxyMetrics
from routemesh.proxy.backpressure import BackpressureLimiter, Overloaded
from routemesh.proxy.forwarder import HttpForwarder
from routemesh.proxy.router import ProxyRouter
from routemesh.proxy.routes_proxy import proxy_request

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated app instance and its shared asynchronous resources."""
    active_settings = settings or get_settings()
    config, backend_configs = load_config(active_settings.config_path)
    registry = BackendRegistry(backend_configs)
    metrics = ProxyMetrics()
    decisions = DecisionLog()
    events = EventStream()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Create shared transport and background health checks once per worker."""
        configure_logging(active_settings.log_level)
        limits = httpx.Limits(max_connections=1000, max_keepalive_connections=100)
        async with httpx.AsyncClient(
            limits=limits,
            follow_redirects=False,
            timeout=httpx.Timeout(5.0, connect=1.0),
        ) as client:
            app.state.http_client = client
            app.state.forwarder = HttpForwarder(
                client,
                float(config.timeouts["connect_s"]),
                float(config.timeouts["read_s"]),
                active_settings.max_body_bytes,
                float(config.timeouts.get("total_s", config.timeouts["read_s"])),
                active_settings.trusted_proxy_hosts,
            )
            app.state.router = ProxyRouter(
                registry,
                app.state.forwarder,
                config,
                metrics,
                decisions,
                events,
            )
            app.state.registry = registry
            app.state.events = events
            app.state.decisions = decisions
            app.state.metrics = metrics
            app.state.settings = active_settings
            app.state.config = config
            app.state.limiter = BackpressureLimiter(int(config.backpressure["max_in_flight"]))
            checker = HealthChecker(
                registry,
                float(config.health["interval_s"]),
                client,
                int(config.health["failure_threshold"]),
                int(config.health["recovery_successes"]),
            )
            app.state.health_checker = checker
            task = asyncio.create_task(checker.run(), name="backend-health-checker")
            admin_app = create_admin_app(active_settings, metrics)
            for state_name in (
                "http_client",
                "router",
                "registry",
                "events",
                "decisions",
                "config",
                "health_checker",
            ):
                setattr(admin_app.state, state_name, getattr(app.state, state_name))
            admin_server = uvicorn.Server(
                uvicorn.Config(
                    admin_app,
                    host=active_settings.admin_host,
                    port=active_settings.admin_port,
                    log_config=None,
                    lifespan="off",
                )
            )
            admin_task = asyncio.create_task(admin_server.serve(), name="routemesh-admin-listener")
            while not admin_server.started:
                if admin_task.done():
                    await admin_task
                await asyncio.sleep(0.01)
            app.state.admin_server = admin_server
            yield
            admin_server.should_exit = True
            await admin_task
            await checker.stop()
            await task

    app = FastAPI(
        title="RouteMesh",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.dashboard_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )

    @app.exception_handler(Overloaded)
    async def overloaded_handler(request: Request, exc: Overloaded) -> JSONResponse:
        """Translate overload into an explicit retryable service response."""
        return JSONResponse({"detail": str(exc)}, status_code=503, headers={"Retry-After": "1"})

    @app.exception_handler(ConfigurationError)
    async def configuration_error(request: Request, exc: ConfigurationError) -> JSONResponse:
        """Surface invalid runtime policy choices as client errors."""
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.api_route(
        "/{path:path}",
        methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    async def catch_all(request: Request, path: str) -> Response:
        """Send application traffic through the shared router and forwarder."""
        return await proxy_request(request, path)

    return app
