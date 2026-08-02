from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerAddressCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    recipient_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=6, max_length=40)
    address_line1: str = Field(min_length=5, max_length=300)
    address_line2: str | None = Field(default=None, max_length=300)
    city: str = Field(min_length=2, max_length=120)
    province: str = Field(min_length=2, max_length=120)
    postal_code: str = Field(min_length=3, max_length=20)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    is_default: bool = False


class CustomerAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    label: str
    recipient_name: str
    phone: str
    address_line1: str
    address_line2: str | None
    city: str
    province: str
    postal_code: str
    latitude: Decimal | None
    longitude: Decimal | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class BookingCreateRequest(BaseModel):
    service_id: UUID
    address_id: UUID
    scheduled_start: datetime
    timezone: str = Field(default="Asia/Jakarta", min_length=1, max_length=64)
    order_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("scheduled_start")
    @classmethod
    def scheduled_start_requires_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduled_start must include timezone")
        return value


class BookingAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    professional_id: UUID
    assigned_by_user_id: UUID
    status: str
    response_reason: str | None
    assigned_at: datetime
    responded_at: datetime | None
    completed_at: datetime | None


class TrackingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    professional_id: UUID
    status: str
    consented_at: datetime
    started_at: datetime
    expires_at: datetime
    stopped_at: datetime | None


class TrackingPingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    session_id: UUID
    professional_id: UUID
    latitude: Decimal
    longitude: Decimal
    accuracy_meters: Decimal | None
    heading_degrees: Decimal | None
    speed_mps: Decimal | None
    recorded_at: datetime


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    customer_id: UUID
    partner_id: UUID
    service_id: UUID
    order_id: UUID | None
    address_id: UUID | None
    professional_id: UUID | None
    status: str
    scheduled_start: datetime
    scheduled_end: datetime
    timezone: str
    service_name: str
    service_duration_minutes: int
    currency: str
    amount: int
    address_snapshot: dict[str, object]
    customer_notes: str | None
    partner_notes: str | None
    cancellation_reason: str | None
    version: int
    confirmed_at: datetime | None
    assigned_at: datetime | None
    started_trip_at: datetime | None
    arrived_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    no_show_at: datetime | None
    created_at: datetime
    updated_at: datetime
    assignment: BookingAssignmentResponse | None = None
    tracking: TrackingSessionResponse | None = None
    latest_location: TrackingPingResponse | None = None


class BookingListResponse(BaseModel):
    data: list[BookingResponse]


class BookingAssignRequest(BaseModel):
    professional_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class BookingReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class VerificationIssueResponse(BaseModel):
    booking_id: UUID
    purpose: Literal["check_in", "check_out"]
    otp: str
    expires_at: datetime


class VerificationRequest(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


class BookingCompleteRequest(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")
    checklist: dict[str, object] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=4000)


class TrackingConsentRequest(BaseModel):
    ttl_minutes: int = Field(default=120, ge=15, le=480)


class TrackingPingRequest(BaseModel):
    professional_id: UUID
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    accuracy_meters: Decimal | None = Field(default=None, ge=0, le=10000)
    heading_degrees: Decimal | None = Field(default=None, ge=0, lt=360)
    speed_mps: Decimal | None = Field(default=None, ge=0, le=200)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_requires_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include timezone")
        return value


class MessageResponse(BaseModel):
    message: str
