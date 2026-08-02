from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SnapshotRequest(BaseModel):
    period_days: int = Field(default=7, ge=1, le=365)


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    partner_id: UUID
    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    currency: str
    metrics: dict[str, Any]
    comparison_metrics: dict[str, Any]
    engine_version: str
    created_at: datetime


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    partner_id: UUID
    snapshot_id: UUID
    category: str
    severity: str
    title: str
    summary: str
    recommendation: str
    evidence: dict[str, Any]
    status: str
    generated_at: datetime
    dismissed_at: datetime | None


class DashboardResponse(BaseModel):
    snapshot: SnapshotResponse
    insights: list[InsightResponse]


class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    partner_id: UUID
    created_by_user_id: UUID
    title: str
    status: str
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    partner_id: UUID
    user_id: UUID | None
    role: str
    intent: str | None
    content: str
    evidence: dict[str, Any]
    model_provider: str
    model_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    created_at: datetime


class SessionDetail(SessionResponse):
    messages: list[MessageResponse]


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    message_id: UUID
    session_id: UUID
    partner_id: UUID
    user_id: UUID
    rating: int
    helpful: bool
    comment: str | None
    created_at: datetime


class ScheduleUpdate(BaseModel):
    timezone: str = Field(default="Asia/Jakarta", min_length=1, max_length=64)
    weekday: int = Field(default=0, ge=0, le=6)
    hour: int = Field(default=8, ge=0, le=23)
    enabled: bool = False


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    partner_id: UUID
    cadence: str
    timezone: str
    weekday: int
    hour: int
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class UsageSummary(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    estimated_cost_minor: int
    currency: str
