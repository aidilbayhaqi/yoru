import uuid

import pytest
from pydantic import ValidationError

from yoru_api.modules.advisor.domain import (
    Candidate,
    assess_safety,
    evaluate_cases,
    rank_candidates,
    request_fingerprint,
    tokenize,
)
from yoru_api.modules.advisor.schemas import AdvisorSessionCreate, MediaRegister


def candidate(*, title: str, description: str, item_type: str = "service") -> Candidate:
    return Candidate(
        item_type=item_type,
        item_id=uuid.uuid4(),
        partner_id=uuid.uuid4(),
        title=title,
        description=description,
        price_minor=125_000,
        currency="IDR",
    )


def test_tokenize_normalizes_and_removes_common_words() -> None:
    assert tokenize("Saya ingin Cleaning DAN konsultasi") == frozenset(
        {"cleaning", "konsultasi"}
    )


def test_safety_blocks_emergency_request() -> None:
    result = assess_safety("Saya mengalami pendarahan berat sekarang")
    assert result.status == "blocked"
    assert result.reason == "medical_emergency"
    assert result.guidance is not None


def test_safety_marks_sensitive_health_for_review() -> None:
    result = assess_safety("Saya punya alergi dan mencari layanan yang sesuai")
    assert result.status == "review"
    assert result.reason == "sensitive_health"


def test_safety_allows_normal_marketplace_request() -> None:
    result = assess_safety("Butuh jasa cleaning rumah mingguan")
    assert result.status == "clear"
    assert result.reason is None


def test_rank_candidates_is_grounded_in_matching_catalog_text() -> None:
    matching = candidate(
        title="Home Deep Cleaning",
        description="Pembersihan rumah menyeluruh dan mingguan",
    )
    unrelated = candidate(
        title="Konsultasi Desain",
        description="Perencanaan interior dan warna",
    )
    ranked = rank_candidates("cleaning rumah mingguan", [unrelated, matching])
    assert len(ranked) == 1
    assert ranked[0].candidate.item_id == matching.item_id
    assert "cleaning" in ranked[0].matched_terms


def test_rank_candidates_returns_empty_without_evidence() -> None:
    ranked = rank_candidates(
        "servis sepeda",
        [candidate(title="Konsultasi Pajak", description="Pelaporan usaha")],
    )
    assert ranked == []


def test_request_fingerprint_is_order_stable() -> None:
    first = request_fingerprint(
        goal="Cleaning rumah",
        concerns=["debu", "waktu"],
        preferences={"area": "Jakarta", "jadwal": "pagi"},
    )
    second = request_fingerprint(
        goal="Cleaning rumah",
        concerns=["waktu", "debu"],
        preferences={"jadwal": "pagi", "area": "Jakarta"},
    )
    assert first == second
    assert len(first) == 64


def test_evaluation_metrics_are_deterministic() -> None:
    metrics = evaluate_cases(
        [
            {
                "query": "butuh cleaning rumah",
                "expected_safety": "clear",
                "expected_terms": ["cleaning", "rumah"],
            },
            {
                "query": "pendarahan berat",
                "expected_safety": "blocked",
                "expected_terms": ["pendarahan"],
            },
        ]
    )
    assert metrics["cases"] == 2
    assert metrics["safety_accuracy"] == 1.0
    assert metrics["term_coverage"] == 1.0


def test_session_schema_rejects_short_goal() -> None:
    with pytest.raises(ValidationError):
        AdvisorSessionCreate(goal="x")


def test_media_schema_rejects_unsupported_content_type() -> None:
    with pytest.raises(ValidationError):
        MediaRegister(
            original_filename="payload.svg",
            content_type="image/svg+xml",
            size_bytes=100,
            sha256="a" * 64,
        )
