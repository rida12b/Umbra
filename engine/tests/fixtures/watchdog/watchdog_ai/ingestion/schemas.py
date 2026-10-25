"""Pydantic schemas for telemetry events ingested by Watchdog."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    """Telemetry event sent by a monitored agent."""

    # Identity
    event_id: UUID
    agent_id: str = Field(min_length=1, max_length=128)
    schema_version: str = "1.0"

    # Timing
    timestamp_start: datetime
    latency_ms: int = Field(ge=0)

    # LLM core
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    prompt: str
    output: str

    # LLM metrics
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)

    # status
    status: Literal["success", "error", "timeout", "content_filter", "rate_limit"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventOut(EventIn):
    tenant_id: str = Field(min_length=1, max_length=128)
    received_at: datetime
