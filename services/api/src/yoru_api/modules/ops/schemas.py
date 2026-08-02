from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpsJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_type: str
    status: str
    started_by_user_id: UUID
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    summary: dict[str, Any]
    error_message: str | None


class RestoreDrillCreate(BaseModel):
    successful: bool
    duration_ms: int = Field(ge=0, le=86_400_000)
    backup_reference: str = Field(min_length=3, max_length=500)
    restored_database: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class RetentionRunResponse(BaseModel):
    job: OpsJobResponse
    results: dict[str, int]


class SecurityEventCreate(BaseModel):
    severity: Literal["info", "low", "medium", "high", "critical"]
    event_type: str = Field(min_length=3, max_length=100)
    source: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=3, max_length=4000)
    request_id: str | None = Field(default=None, max_length=128)
    ip_prefix: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityEventResolve(BaseModel):
    status: Literal["acknowledged", "resolved"]
    note: str = Field(min_length=3, max_length=4000)


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    severity: str
    event_type: str
    source: str
    status: str
    actor_user_id: UUID | None
    request_id: str | None
    ip_prefix: str | None
    description: str
    event_metadata: dict[str, Any]
    occurred_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    resolution_note: str | None


class LaunchGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    release_version: str
    expected_alembic_head: str
    status: str
    checks: list[dict[str, Any]]
    evaluated_by_user_id: UUID
    evaluated_at: datetime


class ReadinessResponse(BaseModel):
    status: Literal["pass", "warn", "fail"]
    release_version: str
    current_alembic_head: str | None
    checks: list[dict[str, Any]]
