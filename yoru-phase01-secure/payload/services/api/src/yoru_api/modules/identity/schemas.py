from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        categories = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if sum(categories) < 3:
            raise ValueError("Password must use at least three character categories")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    status: str


class MembershipResponse(BaseModel):
    partner_id: UUID
    partner_status: str
    membership_status: str
    role: str
    permissions: list[str]


class SessionResponse(BaseModel):
    user: UserResponse
    active_partner_id: UUID | None
    platform_roles: list[str]
    permissions: list[str]
    memberships: list[MembershipResponse]


class SelectPartnerRequest(BaseModel):
    partner_id: UUID | None


class MessageResponse(BaseModel):
    message: str


class SessionListItem(BaseModel):
    id: UUID
    active_partner_id: UUID | None
    created_at: datetime
    last_used_at: datetime
    current: bool
