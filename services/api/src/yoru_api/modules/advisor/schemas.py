from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsentCreate(BaseModel):
    photo_processing: bool = False
    personalization: bool = False
    retention_days: int = Field(default=30, ge=1, le=365)


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    scope: str
    version: str
    status: str
    photo_processing: bool
    personalization: bool
    retention_days: int
    granted_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class AdvisorSessionCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=4000)
    concerns: list[str] = Field(default_factory=list, max_length=20)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @field_validator("concerns")
    @classmethod
    def validate_concerns(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if any(len(item) > 500 for item in cleaned):
            raise ValueError("Each concern must contain at most 500 characters")
        return cleaned


class MediaRegister(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(ge=1, le=10_485_760)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class MediaScanResult(BaseModel):
    result: Literal["clean", "infected", "error"]
    detail: str | None = Field(default=None, max_length=500)
    scanner: str = Field(default="local-mock", min_length=2, max_length=80)


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    customer_id: UUID
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    scan_result: dict[str, Any]
    retention_expires_at: datetime
    scanned_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    partner_id: UUID
    product_id: UUID | None
    service_id: UUID | None
    item_type: str
    rank: int
    score: float
    title: str
    explanation: str
    evidence: dict[str, Any]
    price_snapshot: int
    currency: str
    created_at: datetime


class AdvisorSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    consent_id: UUID
    status: str
    goal: str
    concerns: list[str]
    preferences: dict[str, Any]
    safety_status: str
    safety_reason: str | None
    model_provider: str
    model_version: str
    summary: str | None
    expires_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdvisorSessionDetail(AdvisorSessionResponse):
    media: list[MediaResponse] = Field(default_factory=list)
    recommendations: list[RecommendationResponse] = Field(default_factory=list)


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    helpful: bool
    reason_codes: list[str] = Field(default_factory=list, max_length=10)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    customer_id: UUID
    rating: int
    helpful: bool
    reason_codes: list[str]
    comment: str | None
    created_at: datetime


class EvaluationCase(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    expected_safety: Literal["clear", "review", "blocked"] = "clear"
    expected_terms: list[str] = Field(default_factory=list, max_length=30)


class EvaluationCreate(BaseModel):
    dataset_name: str = Field(min_length=2, max_length=120)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=200)


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_name: str
    engine_version: str
    status: str
    metrics: dict[str, Any]
    cases: list[dict[str, Any]]
    created_by_user_id: UUID
    started_at: datetime
    completed_at: datetime
    created_at: datetime


class RetentionPurgeResponse(BaseModel):
    sessions_expired: int
    media_deleted: int
