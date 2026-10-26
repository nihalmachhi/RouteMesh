"""Admin controls fail closed unless a private token is configured and supplied."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from routemesh.common.errors import ConfigurationError
from routemesh.common.settings import Settings
from routemesh.proxy.app import create_app

TOKEN = "test-only-token-that-is-long-enough-123456"
CONFIG = Path("configs/routemesh.yaml")


def test_app_rejects_missing_or_example_admin_token() -> None:
    for token in (None, "", "change-me", "example-token", "too-short"):
        with pytest.raises(ConfigurationError, match="ROUTEMESH_ADMIN_TOKEN"):
            create_app(Settings(config_path=CONFIG, admin_token=token))


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("put", "/admin/policy", {"policy": "round_robin"}),
        ("post", "/admin/reset", None),
        (
            "post",
            "/admin/backends/backend-a/behavior",
            {"latency_ms": 10, "jitter_ms": 0, "error_rate": 0, "cpu_percent": 10},
        ),
    ],
)
def test_mutations_reject_missing_and_wrong_tokens(
    method: str, path: str, body: dict[str, object] | None
) -> None:
    app = create_app(Settings(config_path=CONFIG, admin_token=TOKEN))
    with TestClient(app) as client:
        assert client.request(method, path, json=body).status_code == 401
        assert client.request(
            method, path, json=body, headers={"X-RouteMesh-Admin-Token": "wrong-token"}
        ).status_code == 401


def test_valid_token_can_change_policy() -> None:
    app = create_app(Settings(config_path=CONFIG, admin_token=TOKEN))
    with TestClient(app) as client:
        response = client.put(
            "/admin/policy",
            json={"policy": "round_robin"},
            headers={"X-RouteMesh-Admin-Token": TOKEN},
        )
    assert response.status_code == 200
    assert response.json() == {"policy": "round_robin"}
