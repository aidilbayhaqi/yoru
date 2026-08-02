from datetime import datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CatalogStatus = Literal[
    "draft",
    "pending_review",
    "published",
    "revision_required",
    "rejected",
    "archived",
]


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None


class CreateProductRequest(BaseModel):
    category_id: UUID
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    stock_tracked: bool = True
    initial_stock: int = Field(default=0, ge=0, le=2_000_000_000)
    reorder_level: int = Field(default=0, ge=0, le=2_000_000_000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class UpdateProductRequest(BaseModel):
    category_id: UUID | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stock_tracked: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class RegisterProductMediaRequest(BaseModel):
    object_key: str = Field(min_length=3, max_length=500)
    content_type: str = Field(min_length=3, max_length=120)
    alt_text: str | None = Field(default=None, max_length=200)
    sort_order: int = Field(default=0, ge=0, le=1000)


class ProductMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    object_key: str
    content_type: str
    alt_text: str | None
    sort_order: int
    status: str
    created_at: datetime


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    on_hand: int
    reserved: int
    available: int
    reorder_level: int
    version: int
    updated_at: datetime


class UpdateInventoryRequest(BaseModel):
    on_hand: int = Field(ge=0, le=2_000_000_000)
    reorder_level: int = Field(default=0, ge=0, le=2_000_000_000)
    expected_version: int | None = Field(default=None, ge=1)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    category_id: UUID
    sku: str | None
    name: str
    slug: str
    description: str
    unit_price: Decimal
    currency: str
    stock_tracked: bool
    status: CatalogStatus
    review_reason: str | None
    submitted_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    available_quantity: int | None = None
    inventory: InventoryResponse | None = None
    media: list[ProductMediaResponse] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    data: list[ProductResponse]


class CreateServiceRequest(BaseModel):
    category_id: UUID
    name: str = Field(min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    duration_minutes: int = Field(ge=5, le=1440)
    price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    capacity_per_slot: int = Field(default=1, ge=1, le=10000)
    booking_notice_minutes: int = Field(default=0, ge=0, le=525600)
    cancellation_window_minutes: int = Field(default=0, ge=0, le=525600)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class UpdateServiceRequest(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    capacity_per_slot: int | None = Field(default=None, ge=1, le=10000)
    booking_notice_minutes: int | None = Field(default=None, ge=0, le=525600)
    cancellation_window_minutes: int | None = Field(default=None, ge=0, le=525600)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ProfessionalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    name: str
    title: str | None
    bio: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateProfessionalRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    title: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=5000)


class CreateAvailabilityRequest(BaseModel):
    professional_id: UUID | None = None
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    timezone: str = Field(default="Asia/Jakarta", min_length=3, max_length=64)
    slot_interval_minutes: int = Field(default=30, ge=5, le=1440)
    capacity_override: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CreateAvailabilityRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    professional_id: UUID | None
    weekday: int
    start_time: time
    end_time: time
    timezone: str
    slot_interval_minutes: int
    capacity_override: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    category_id: UUID
    name: str
    slug: str
    description: str
    duration_minutes: int
    price: Decimal
    currency: str
    capacity_per_slot: int
    booking_notice_minutes: int
    cancellation_window_minutes: int
    status: CatalogStatus
    review_reason: str | None
    submitted_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    availability: list[AvailabilityResponse] = Field(default_factory=list)
    professionals: list[ProfessionalResponse] = Field(default_factory=list)


class ServiceListResponse(BaseModel):
    data: list[ServiceResponse]


class ModerationRequest(BaseModel):
    decision: Literal["publish", "revision_required", "reject"]
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_reason_for_negative_decision(self) -> "ModerationRequest":
        if self.decision != "publish" and not self.reason:
            raise ValueError("reason is required for revision or rejection")
        return self
