from uuid import uuid4

import pytest
from pydantic import ValidationError

from yoru_api.modules.identity.permissions import (
    Actor,
    MembershipContext,
    require_permission,
)
from yoru_api.modules.identity.schemas import RegisterRequest
from yoru_api.modules.identity.security import (
    hash_password,
    hash_token,
    normalize_email,
    verify_password,
)


def _actor(
    *,
    partner_id=None,
    partner_status: str = "verified",
    membership_status: str = "active",
    permissions: frozenset[str] = frozenset(),
    platform_permissions: frozenset[str] = frozenset(),
) -> Actor:
    membership = (
        MembershipContext(
            partner_id=partner_id,
            partner_status=partner_status,
            membership_status=membership_status,
            role="partner_admin",
            permissions=permissions,
        )
        if partner_id
        else None
    )
    return Actor(
        user_id=uuid4(),
        email="user@yoru.test",
        full_name="Yoru User",
        status="active",
        session_id=uuid4(),
        active_partner_id=partner_id,
        platform_roles=frozenset(),
        platform_permissions=platform_permissions,
        memberships=(membership,) if membership else (),
    )


def test_argon2_password_hash_roundtrip() -> None:
    encoded = hash_password("StrongPassword!2026")

    assert encoded.startswith("$argon2")
    assert verify_password("StrongPassword!2026", encoded)
    assert not verify_password("wrong-password", encoded)


def test_email_normalization_and_keyed_token_hash() -> None:
    assert normalize_email("  CUSTOMER@YORU.TEST ") == "customer@yoru.test"
    assert hash_token("token", "secret-a") == hash_token("token", "secret-a")
    assert hash_token("token", "secret-a") != hash_token("token", "secret-b")


def test_weak_password_is_rejected() -> None:
    with pytest.raises(ValidationError, match="character categories"):
        RegisterRequest(
            email="customer@yoru.test",
            full_name="Customer",
            password="alllowercase",
        )


def test_cross_tenant_access_is_denied() -> None:
    own_partner = uuid4()
    actor = _actor(
        partner_id=own_partner,
        permissions=frozenset({"catalog.product.write"}),
    )

    with pytest.raises(Exception, match="Tenant scope denied"):
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=uuid4(),
            require_partner_write=True,
        )


def test_suspended_partner_cannot_write() -> None:
    partner_id = uuid4()
    actor = _actor(
        partner_id=partner_id,
        partner_status="suspended",
        permissions=frozenset({"catalog.product.write"}),
    )

    with pytest.raises(Exception, match="Partner cannot perform writes"):
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=partner_id,
            require_partner_write=True,
        )


def test_role_without_capability_is_denied() -> None:
    actor = _actor(partner_id=uuid4(), permissions=frozenset({"finance.ledger.read"}))

    with pytest.raises(Exception, match="Permission denied"):
        require_permission(actor, "catalog.product.write")


def test_platform_permission_can_cross_tenant_but_still_requires_mfa() -> None:
    actor = _actor(platform_permissions=frozenset({"platform.payout.approve"}))

    with pytest.raises(Exception, match="Recent MFA"):
        require_permission(
            actor,
            "platform.payout.approve",
            partner_id=uuid4(),
            require_mfa=True,
        )
