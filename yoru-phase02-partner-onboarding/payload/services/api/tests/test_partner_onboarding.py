import pytest
from pydantic import ValidationError

from yoru_api.core.problem import AppError
from yoru_api.modules.partners.schemas import (
    CreateServiceAreaRequest,
    ScanResultRequest,
)
from yoru_api.modules.partners.state_machine import ensure_partner_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "submitted"),
        ("submitted", "under_review"),
        ("under_review", "revision_required"),
        ("under_review", "verified"),
        ("under_review", "rejected"),
        ("revision_required", "submitted"),
        ("verified", "suspended"),
        ("suspended", "verified"),
    ],
)
def test_valid_partner_transitions(current: str, target: str) -> None:
    ensure_partner_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "verified"),
        ("submitted", "verified"),
        ("revision_required", "verified"),
        ("rejected", "submitted"),
        ("suspended", "submitted"),
    ],
)
def test_invalid_partner_transitions_raise_conflict(current: str, target: str) -> None:
    with pytest.raises(AppError) as error:
        ensure_partner_transition(current, target)
    assert error.value.status_code == 409
    assert error.value.code == "PARTNER_STATE_CONFLICT"


def test_radius_service_area_requires_complete_coordinates() -> None:
    with pytest.raises(ValidationError):
        CreateServiceAreaRequest(name="Jakarta", area_type="radius", radius_km=20)


def test_postal_service_area_normalizes_codes() -> None:
    payload = CreateServiceAreaRequest(
        name="Jabodetabek",
        area_type="postal_codes",
        postal_codes=[" 16412 ", "16412", "12190"],
    )
    assert payload.postal_codes == ["12190", "16412"]


def test_scan_result_rejects_quarantined_state() -> None:
    with pytest.raises(ValidationError):
        ScanResultRequest(status="quarantined")


def _submission_bundle(*, owner_identity_expires_at=None):
    from datetime import UTC, datetime
    from uuid import uuid4

    from yoru_api.modules.identity.models import Partner
    from yoru_api.modules.partners.models import (
        PartnerDocument,
        PartnerVerification,
        ServiceArea,
    )
    from yoru_api.modules.partners.repository import PartnerBundle

    partner_id = uuid4()
    user_id = uuid4()
    now = datetime.now(UTC)
    partner = Partner(
        id=partner_id,
        display_name="Mitra Sehat",
        legal_name="PT Mitra Sehat Indonesia",
        partner_type="company",
        contact_email="owner@example.com",
        contact_phone="081234567890",
        address_line="Jalan Contoh 1",
        city="Jakarta",
        province="DKI Jakarta",
        status="draft",
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    verification = PartnerVerification(
        id=uuid4(),
        partner_id=partner_id,
        status="draft",
        checklist={},
        created_at=now,
        updated_at=now,
    )
    documents = [
        PartnerDocument(
            id=uuid4(),
            partner_id=partner_id,
            kind="business_registration",
            object_key=f"quarantine/{uuid4()}",
            original_filename="nib.pdf",
            content_type="application/pdf",
            size_bytes=100,
            scan_status="clean",
            verification_status="pending",
            uploaded_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        ),
        PartnerDocument(
            id=uuid4(),
            partner_id=partner_id,
            kind="owner_identity",
            object_key=f"quarantine/{uuid4()}",
            original_filename="ktp.pdf",
            content_type="application/pdf",
            size_bytes=100,
            scan_status="clean",
            verification_status="pending",
            expires_at=owner_identity_expires_at,
            uploaded_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        ),
    ]
    service_areas = [
        ServiceArea(
            id=uuid4(),
            partner_id=partner_id,
            name="Jakarta",
            area_type="radius",
            center_latitude=-6.2,
            center_longitude=106.8,
            radius_km=20,
            postal_codes=[],
            status="pending",
            created_at=now,
            updated_at=now,
        )
    ]
    return PartnerBundle(partner, verification, documents, service_areas)


def test_complete_submission_bundle_passes_gate() -> None:
    from yoru_api.modules.partners.service import PartnerService

    PartnerService._validate_submission(_submission_bundle())


def test_expired_required_document_fails_submission_gate() -> None:
    from datetime import UTC, datetime, timedelta

    from yoru_api.modules.partners.service import PartnerService

    bundle = _submission_bundle(
        owner_identity_expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    with pytest.raises(AppError) as error:
        PartnerService._validate_submission(bundle)
    assert error.value.code == "PARTNER_DOCUMENTS_INCOMPLETE"
