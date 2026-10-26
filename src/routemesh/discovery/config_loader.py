"""Load and validate static YAML service and resilience configuration."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from routemesh.common.errors import ConfigurationError
from routemesh.discovery.models import BackendConfig

RequiredKeys = dict[str, tuple[str, ...]]


class BackendYaml(BaseModel):
    """Validated backend entry from routemesh.yaml."""

    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    url: str = Field(min_length=1)


class RouteConfig(BaseModel):
    """Validated application policy and resilience configuration."""

    policy: Literal["round_robin", "least_connections", "latency_aware"]
    timeouts: dict[str, float]
    backpressure: dict[str, int]
    retries: dict[str, float | int]
    health: dict[str, float | int]
    circuit_breaker: dict[str, float | int]
    scoring: dict[str, float]
    backends: list[BackendYaml] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sections(self) -> "RouteConfig":
        """Fail at startup when any required operational setting is absent."""
        required: RequiredKeys = {
            "timeouts": ("connect_s", "read_s"),
            "backpressure": ("max_in_flight",),
            "retries": ("max_attempts", "budget_ratio"),
            "health": ("interval_s", "failure_threshold", "recovery_successes"),
            "circuit_breaker": ("consecutive_failures", "window", "error_rate", "open_s"),
            "scoring": ("w_latency", "w_cpu", "w_error", "ewma_alpha"),
        }
        sections: dict[str, Mapping[str, float | int]] = {
            "timeouts": self.timeouts,
            "backpressure": self.backpressure,
            "retries": self.retries,
            "health": self.health,
            "circuit_breaker": self.circuit_breaker,
            "scoring": self.scoring,
        }
        for section, keys in required.items():
            missing = set(keys) - sections[section].keys()
            if missing:
                raise ValueError(f"{section} missing required keys: {sorted(missing)}")
        if min(self.timeouts.values()) <= 0 or min(self.health.values()) <= 0:
            raise ValueError("timeouts and health values must be positive")
        if int(self.backpressure["max_in_flight"]) < 1:
            raise ValueError("max_in_flight must be positive")
        if int(self.retries["max_attempts"]) < 1:
            raise ValueError("max_attempts must be positive")
        if not 0 <= float(self.retries["budget_ratio"]) <= 1:
            raise ValueError("retry budget ratio must be between zero and one")
        if not 0 <= float(self.circuit_breaker["error_rate"]) <= 1:
            raise ValueError("circuit error rate must be between zero and one")
        if not 0 < float(self.scoring["ewma_alpha"]) <= 1:
            raise ValueError("EWMA alpha must be within (0, 1]")
        weights = [float(self.scoring[key]) for key in ("w_latency", "w_cpu", "w_error")]
        if min(weights) < 0 or abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError("latency, CPU, and error weights must be non-negative and sum to one")
        for backend in self.backends:
            parsed = urlparse(backend.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"backend {backend.id} must use an absolute HTTP(S) URL")
        ids = [backend.id for backend in self.backends]
        if len(ids) != len(set(ids)):
            raise ValueError("backend IDs must be unique")
        return self


def load_config(path: Path) -> tuple[RouteConfig, list[BackendConfig]]:
    """Parse YAML, validate all sections, and create immutable endpoint configs."""
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = RouteConfig.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"cannot load RouteMesh configuration: {exc}") from exc
    backends = [BackendConfig(item.id, item.url.rstrip("/")) for item in config.backends]
    return config, backends
