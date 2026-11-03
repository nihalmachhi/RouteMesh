from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from routemesh.core.settings import Settings
from routemesh.discovery.config_loader import RouteConfig, load_config


def test_default_route_configuration_is_valid():
    config, backends = load_config(Path("configs/routemesh.yaml"))
    assert config.policy == "latency_aware"
    assert len(backends) == 3
    assert config.timeouts["total_s"] == 15
    values = yaml.safe_load(Path("configs/routemesh.yaml").read_text(encoding="utf-8"))
    values["policy"] = "bandit_thompson"
    assert RouteConfig.model_validate(values).policy == "bandit_thompson"


def test_settings_rejects_admin_wildcard_bind_outside_container():
    with pytest.raises(ValidationError, match="admin listener must use loopback"):
        Settings(admin_host="0.0.0.0")  # noqa: S104


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("timeouts", "total_s", -1),
        ("retries", "budget_ratio", 2),
        ("scoring", "w_in_flight", -0.1),
        ("backends", 0, {"id": "bad", "url": "file:///etc/passwd"}),
    ],
)
def test_route_configuration_rejects_unsafe_values(section, key, value):
    values = yaml.safe_load(Path("configs/routemesh.yaml").read_text(encoding="utf-8"))
    if section == "backends":
        values[section][key] = value
    else:
        values[section][key] = value
    with pytest.raises(ValidationError):
        RouteConfig.model_validate(values)
