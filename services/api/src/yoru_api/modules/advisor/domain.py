from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from yoru_api.modules.advisor import ENGINE_VERSION

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

_BLOCKED_PATTERNS: tuple[tuple[str, str], ...] = (
    ("bunuh diri", "self_harm"),
    ("menyakiti diri", "self_harm"),
    ("overdosis", "medical_emergency"),
    ("sesak napas berat", "medical_emergency"),
    ("pendarahan berat", "medical_emergency"),
    ("tidak sadarkan diri", "medical_emergency"),
    ("bom", "violent_harm"),
    ("racun", "dangerous_substance"),
)

_REVIEW_PATTERNS: tuple[tuple[str, str], ...] = (
    ("hamil", "sensitive_health"),
    ("alergi", "sensitive_health"),
    ("obat", "sensitive_health"),
    ("diagnosis", "medical_claim"),
    ("darurat", "possible_emergency"),
)

_STOPWORDS = frozenset(
    {
        "yang",
        "dan",
        "atau",
        "untuk",
        "dengan",
        "saya",
        "aku",
        "ingin",
        "mau",
        "butuh",
        "cari",
        "tolong",
        "the",
        "and",
        "for",
        "with",
        "want",
        "need",
    }
)


@dataclass(frozen=True, slots=True)
class SafetyAssessment:
    status: str
    reason: str | None
    guidance: str | None


@dataclass(frozen=True, slots=True)
class Candidate:
    item_type: str
    item_id: UUID
    partner_id: UUID
    title: str
    description: str
    price_minor: int
    currency: str


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: Candidate
    score: float
    matched_terms: tuple[str, ...]


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def tokenize(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _TOKEN_PATTERN.findall(normalize_text(value))
        if len(token) >= 2 and token not in _STOPWORDS
    )


def request_fingerprint(
    *, goal: str, concerns: Sequence[str], preferences: Mapping[str, object]
) -> str:
    preference_text = "|".join(
        f"{key}={preferences[key]}" for key in sorted(preferences)
    )
    material = "\n".join((goal, *sorted(concerns), preference_text))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def assess_safety(text: str) -> SafetyAssessment:
    normalized = normalize_text(text)
    for pattern, reason in _BLOCKED_PATTERNS:
        if pattern in normalized:
            return SafetyAssessment(
                status="blocked",
                reason=reason,
                guidance=(
                    "Permintaan ini membutuhkan bantuan manusia yang tepat dan tidak "
                    "diproses sebagai rekomendasi marketplace."
                ),
            )
    for pattern, reason in _REVIEW_PATTERNS:
        if pattern in normalized:
            return SafetyAssessment(
                status="review",
                reason=reason,
                guidance=(
                    "Rekomendasi dibatasi pada informasi katalog dan tidak menggantikan "
                    "penilaian profesional."
                ),
            )
    return SafetyAssessment(status="clear", reason=None, guidance=None)


def rank_candidates(
    query: str,
    candidates: Iterable[Candidate],
    *,
    limit: int = 5,
) -> list[RankedCandidate]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        title_tokens = tokenize(candidate.title)
        description_tokens = tokenize(candidate.description)
        matched_title = query_tokens & title_tokens
        matched_description = query_tokens & description_tokens
        matched = matched_title | matched_description
        if not matched:
            continue

        title_score = len(matched_title) / max(len(query_tokens), 1)
        description_score = len(matched_description) / max(len(query_tokens), 1)
        coverage = len(matched) / max(len(query_tokens), 1)
        score = round((title_score * 0.55) + (description_score * 0.25) + (coverage * 0.20), 6)
        ranked.append(
            RankedCandidate(
                candidate=candidate,
                score=score,
                matched_terms=tuple(sorted(matched)),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.score,
            item.candidate.item_type,
            item.candidate.title.lower(),
            str(item.candidate.item_id),
        )
    )
    return ranked[: max(1, min(limit, 10))]


def build_explanation(item: RankedCandidate) -> str:
    terms = ", ".join(item.matched_terms)
    return (
        f"Direkomendasikan karena informasi katalog cocok dengan istilah: {terms}. "
        "Periksa detail, harga, ketersediaan, serta kecocokan langsung dengan partner."
    )


def evaluate_cases(cases: Sequence[Mapping[str, object]]) -> dict[str, float | int | str]:
    total = len(cases)
    if total == 0:
        return {
            "engine_version": ENGINE_VERSION,
            "cases": 0,
            "safety_accuracy": 0.0,
            "term_coverage": 0.0,
        }

    safety_correct = 0
    coverage_total = 0.0
    for case in cases:
        query = str(case.get("query", ""))
        expected_status = str(case.get("expected_safety", "clear"))
        assessment = assess_safety(query)
        safety_correct += int(assessment.status == expected_status)

        expected_terms = {
            normalize_text(str(term))
            for term in case.get("expected_terms", [])  # type: ignore[arg-type]
            if str(term).strip()
        }
        query_tokens = tokenize(query)
        if expected_terms:
            coverage_total += len(expected_terms & query_tokens) / len(expected_terms)
        else:
            coverage_total += 1.0

    return {
        "engine_version": ENGINE_VERSION,
        "cases": total,
        "safety_accuracy": round(safety_correct / total, 6),
        "term_coverage": round(coverage_total / total, 6),
    }
