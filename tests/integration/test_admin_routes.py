from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from routemesh.admin.app import create_admin_app
from routemesh.core.settings import Settings
from routemesh.discovery.models import BackendSnapshot
from routemesh.metrics.decision_log import DecisionLog
from routemesh.metrics.event_stream import EventStream
from routemesh.metrics.prometheus import ProxyMetrics
from routemesh.proxy.app import create_app


class RegistryStub:
    async def snapshots(self):
        return [BackendSnapshot("backend-a", "http://backend-a", True)]


class PolicyStub:
    def __init__(self):
        self.name = "round_robin"

    async def current(self):
        return self.name, 0

    async def select(self, name):
        self.name = name


class RouterStub:
    def __init__(self):
        self.policy = PolicyStub()
        self.breakers = {"backend-a": SimpleNamespace(state="closed")}
        self.request_counts = {"backend-a": 0}
        self.reset_called = False

    async def reset_observations(self):
        self.reset_called = True


class HttpClientStub:
    async def post(self, url, json):
        return SimpleNamespace(json=lambda: {"down": False}, raise_for_status=lambda: None)


def make_app():
    settings = Settings(admin_token="test-token", admin_port=0)
    app = create_admin_app(settings, ProxyMetrics())
    app.state.registry = RegistryStub()
    app.state.router = RouterStub()
    app.state.decisions = DecisionLog()
    app.state.events = EventStream()

    app.state.http_client = HttpClientStub()
    return app


def test_operations_routes_require_auth_and_expose_state_and_controls():
    app = make_app()
    client = TestClient(app)
    try:
        assert client.get("/admin/backends").status_code == 401
        headers = {"X-RouteMesh-Admin-Token": "test-token"}
        assert client.get("/admin/backends", headers=headers).json()[0]["id"] == "backend-a"
        assert client.get("/admin/policy", headers=headers).json() == {"policy": "round_robin"}
        assert client.get("/admin/decisions", headers=headers).json() == []
        assert client.get("/metrics").status_code == 401
        assert client.get("/metrics", headers=headers).status_code == 200
        assert client.put(
            "/admin/policy", headers=headers, json={"policy": "least_connections"}
        ).json() == {"policy": "least_connections"}
        assert client.post("/admin/reset", headers=headers).json() == {"status": "reset"}
        assert app.state.router.reset_called
        changed = client.post(
            "/admin/backends/backend-a/behavior",
            headers=headers,
            json={"latency_ms": 12},
        )
        assert changed.status_code == 200
        assert changed.json()["backend_id"] == "backend-a"
        assert (
            client.post("/admin/backends/unknown/behavior", headers=headers, json={}).status_code
            == 404
        )
    finally:
        client.close()


def test_proxy_health_and_metrics_endpoints_are_available():
    app = create_app(Settings(admin_token="test-token", admin_port=0))
    with TestClient(app):
        assert "/healthz" not in {route.path for route in app.routes}
        assert "/admin/backends" not in {route.path for route in app.routes}
        assert "/metrics" not in {route.path for route in app.routes}
        admin_port = app.state.admin_server.servers[0].sockets[0].getsockname()[1]
        response = httpx.get(
            f"http://127.0.0.1:{admin_port}/admin/policy",
            headers={"X-RouteMesh-Admin-Token": "test-token"},
            timeout=2,
        )
        assert response.status_code == 200


def test_admin_reads_and_writes_fail_closed_without_token():
    app = create_admin_app(Settings(admin_token="", admin_port=0), ProxyMetrics())
    client = TestClient(app)
    try:
        assert client.get("/admin/policy").status_code == 503
        assert client.put("/admin/policy", json={"policy": "round_robin"}).status_code == 503
        assert client.get("/metrics").status_code == 503
    finally:
        client.close()
