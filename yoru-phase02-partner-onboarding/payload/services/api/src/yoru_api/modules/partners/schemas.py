from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class PartnerType(StrEnum):
    COMPANY = "company"
    INDIVIDUAL = "individual"
    CLINIC = "clinic"
    STORE = "store"
    SERVICE_PROVIDER = "service_provider"


class DocumentKind(StrEnum):
    BUSINESS_REGISTRATION = "business_registration"
    OWNER_IDENTITY = "owner_identity"
    TAX_REGISTRATION = "tax_registration"
    PROFESSIONAL_CREDENTIAL = "professional_credential"
    OTHER = "other"


class ScanStatus(StrEnum):
    QUARANTINED = "quarantined"
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


class ReviewDecision(StrEnum):
    VERIFIED = "verified"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"


class CreatePartnerRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=150)
    legal_name: str = Field(min_length=2, max_length=200)
    partner_type: PartnerType
    contact_email: EmailStr
    contact_phone: str = Field(min_length=7, max_length=40)
    address_line: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=2, max_length=120)
    province: str = Field(min_length=2, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class UpdatePartnerRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=150)
    legal_name: str | None = Field(default=None, min_length=2, max_length=200)
    partner_type: PartnerType | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, min_length=7, max_length=40)
    address_line: str | None = Field(default=None, min_length=5, max_length=300)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    province: str | None = Field(default=None, min_length=2, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class RegisterDocumentRequest(BaseModel):
    kind: DocumentKind
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(pattern=r"^(application/pdf|image/jpeg|image/png)$")
    size_bytes: int = Field(ge=1, le=15 * 1024 * 1024)
    expires_at: datetime | None = None


class ScanResultRequest(BaseModel):
    status: ScanStatus
    detail: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def reject_quarantine_as_result(self) -> "ScanResultRequest":
        if self.status == ScanStatus.QUARANTINED:
            raise ValueError("quarantined is an initial state, not a scan result")
        return self


class CreateServiceAreaRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    area_type: str = Field(pattern=r"^(radius|postal_codes)$")
    center_latitude: float | None = Field(default=None, ge=-90, le=90)
    center_longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=500)
    postal_codes: list[str] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_shape(self) -> "CreateServiceAreaRequest":
        if self.area_type == "radius":
            if (
                self.center_latitude is None
                or self.center_longitude is None
                or self.radius_km is None
            ):
                raise ValueError("radius area requires coordinates and radius_km")
            if self.postal_codes:
                raise ValueError("radius area cannot include postal_codes")
        if self.area_type == "postal_codes":
            normalized = sorted({code.strip() for code in self.postal_codes if code.strip()})
            if not normalized:
                raise ValueError("postal_codes area requires at least one postal code")
            self.postal_codes = normalized
            if any(
                value is not None
                for value in (
                    self.center_latitude,
                    self.center_longitude,
                    self.radius_km,
                )
            ):
                raise ValueError("postal_codes area cannot include radius fields")
        return self


class ReviewDecisionRequest(BaseModel):
    decision: ReviewDecision
    reason: str = Field(min_length=10, max_length=2000)
    checklist: dict[str, bool] = Field(default_factory=dict)


class BlockPartnerRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    scan_status: str
    verification_status: str
    expires_at: datetime | None
    scanned_at: datetime | None
    scan_detail: str | None
    created_at: datetime


class ServiceAreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    area_type: str
    center_latitude: float | None
    center_longitude: float | None
    radius_km: float | None
    postal_codes: list[str]
    status: str
    created_at: datetime


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    checklist: dict[str, bool]
    reviewer_id: UUID | None
    reason: str | None
    started_at: datetime | None
    decided_at: datetime | None
    updated_at: datetime


class PartnerResponse(BaseModel):
    id: UUID
    display_name: str
    legal_name: str | None
    partner_type: str | None
    contact_email: str | None
    contact_phone: str | None
    address_line: str | None
    city: str | None
    province: str | None
    postal_code: str | None
    description: str | None
    status: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    review_reason: str | None
    created_at: datetime
    updated_at: datetime
    verification: VerificationResponse
    documents: list[DocumentResponse]
    service_areas: list[ServiceAreaResponse]


class PartnerListResponse(BaseModel):
    data: list[PartnerResponse]
