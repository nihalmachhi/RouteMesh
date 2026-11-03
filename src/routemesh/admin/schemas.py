"""Validated request bodies for local admin and demo controls."""

from pydantic import BaseModel, Field


class PolicyUpdate(BaseModel):
    """Select a registered routing policy."""

    policy: str


class BehaviorUpdate(BaseModel):
    """Bound the fault parameters accepted by demo backend controls."""

    latency_ms: float = Field(default=0, ge=0, le=10_000)
    jitter_ms: float = Field(default=0, ge=0, le=5_000)
    error_rate: float = Field(default=0, ge=0, le=1)
    cpu_percent: float = Field(default=10, ge=0, le=100)
    down: bool = False
