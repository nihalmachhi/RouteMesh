"""Validated settings for the RouteMesh process."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read runtime configuration from environment variables."""

    model_config = SettingsConfigDict(env_prefix="ROUTEMESH_", env_file=".env", extra="ignore")
    config_path: Path = Path("configs/routemesh.yaml")
    log_level: str = "INFO"
    admin_token: str = ""
    admin_port: int = Field(default=9000, ge=0, le=65535)
    admin_host: str = "127.0.0.1"
    request_id_header: str = "X-Request-ID"
    max_body_bytes: int = Field(default=10_000_000, ge=1024)
    trusted_proxy_hosts: list[str] = []
    dashboard_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("admin_host")
    @classmethod
    def validate_admin_host(cls, value: str) -> str:
        """Allow wildcard binding only inside a Docker container boundary."""
        if value in {"127.0.0.1", "::1", "localhost"}:
            return value
        if value == "0.0.0.0" and Path("/.dockerenv").exists():  # noqa: S104
            return value
        raise ValueError("admin listener must use loopback outside a Docker container")


@lru_cache
def get_settings() -> Settings:
    """Return the cached validated settings instance."""
    return Settings()
