from fastapi.testclient import TestClient

from routemesh.demo_backends.app import create_backend_app


def test_demo_backend_echoes_requests_and_applies_fault_controls():
    with TestClient(create_backend_app("test-backend")) as client:
        health = client.get("/health")
        assert health.json()["status"] == "ok"
        assert client.post("/orders", content=b"payload").content == b"payload"
        changed = client.post(
            "/admin/behavior",
            json={"latency_ms": 0, "jitter_ms": 0, "error_rate": 0, "cpu_percent": 75},
        )
        assert changed.json()["cpu_percent"] == 75
        assert client.get("/orders").headers["x-backend-id"] == "test-backend"


def test_demo_backend_can_be_marked_down():
    with TestClient(create_backend_app("test-backend")) as client:
        response = client.post("/admin/behavior", json={"down": True})
        assert response.status_code == 200
        assert client.get("/health").json()["status"] == "down"
        assert client.get("/orders").status_code == 503
