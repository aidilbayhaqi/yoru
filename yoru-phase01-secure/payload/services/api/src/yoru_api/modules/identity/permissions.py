from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from yoru_api.core.problem import AppError


@dataclass(frozen=True, slots=True)
class MembershipContext:
    partner_id: UUID
    partner_status: str
    membership_status: str
    role: str
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    email: str
    full_name: str
    status: str
    session_id: UUID
    active_partner_id: UUID | None
    platform_roles: frozenset[str]
    platform_permissions: frozenset[str]
    memberships: tuple[MembershipContext, ...]
    mfa_verified_at: datetime | None = None

    @property
    def active_membership(self) -> MembershipContext | None:
        if self.active_partner_id is None:
            return None
        return next(
            (
                membership
                for membership in self.memberships
                if membership.partner_id == self.active_partner_id
            ),
            None,
        )

    @property
    def permissions(self) -> frozenset[str]:
        membership = self.active_membership
        partner_permissions = membership.permissions if membership else frozenset()
        return self.platform_permissions | partner_permissions | frozenset({"account.self.read"})

    def has_recent_mfa(self, max_age_seconds: int = 900) -> bool:
        if self.mfa_verified_at is None:
            return False
        age = datetime.now(UTC) - self.mfa_verified_at
        return age.total_seconds() <= max_age_seconds


def require_permission(
    actor: Actor,
    permission: str,
    *,
    partner_id: UUID | None = None,
    require_partner_write: bool = False,
    require_mfa: bool = False,
) -> None:
    if permission not in actor.permissions:
        raise AppError(403, "PERMISSION_DENIED", "Permission denied")
    if partner_id is not None:
        membership = actor.active_membership
        is_platform_actor = permission in actor.platform_permissions
        if not is_platform_actor and (
            membership is None or membership.partner_id != partner_id
        ):
            raise AppError(403, "TENANT_SCOPE_DENIED", "Tenant scope denied")
        if require_partner_write and not is_platform_actor:
            if membership is None or membership.membership_status != "active":
                raise AppError(403, "MEMBERSHIP_INACTIVE", "Membership is not active")
            if membership.partner_status != "verified":
                raise AppError(403, "PARTNER_WRITE_BLOCKED", "Partner cannot perform writes")
    if require_mfa and not actor.has_recent_mfa():
        raise AppError(403, "MFA_STEP_UP_REQUIRED", "Recent MFA verification is required")
