"""Validated settings for the RouteMesh process."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read runtime configuration from environment variables."""

    model_config = SettingsConfigDict(env_prefix="ROUTEMESH_", env_file=".env", extra="ignore")
    config_path: Path = Path("configs/routemesh.yaml")
    log_level: str = "INFO"
    admin_token: str | None = None
    request_id_header: str = "X-Request-ID"
    max_body_bytes: int = Field(default=10_000_000, ge=1024)
    dashboard_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return the cached validated settings instance."""
    return Settings()
