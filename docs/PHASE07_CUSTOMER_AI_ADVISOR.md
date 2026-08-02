# Phase 7 — Customer AI Advisor

Version: `0.8.0`  
Alembic revision: `20260801_0008`

## Purpose

Phase 7 adds a privacy-aware, provider-neutral Customer AI Advisor. The first engine is deterministic and local so the workflow can be tested without an external AI subscription. It only ranks products and services whose catalog status is `published`.

## Delivered capabilities

- Explicit, versioned customer consent with configurable retention.
- Optional photo-processing consent.
- Quarantine-only media metadata registration.
- Mandatory malware-scan result before a session with media can be analyzed.
- Safety screening before catalog ranking.
- Grounded recommendations containing matched catalog terms and source IDs.
- Customer feedback.
- Platform evaluation runs and retention purge.
- Audit and outbox events.
- PostgreSQL row-level security.

## Important boundaries

- The local engine does not diagnose, prescribe, or claim professional certainty.
- Blocked safety requests do not receive marketplace recommendations.
- This patch registers media metadata and scan workflow; it does not include S3/MinIO upload infrastructure or a malware scanner daemon.
- No external model provider is enabled in this phase.
- The `FEATURE_CUSTOMER_AI` flag is disabled by default.

## Event types

- `ai.advisor.session.created`
- `ai.advisor.completed`
- `ai.media.scan.requested`
- `ai.media.scan.clean`
- `ai.media.scan.infected`
- `ai.media.scan.error`

## Production follow-up

Before enabling external model providers, add provider-specific data-processing agreements, encrypted object storage, signed upload URLs, scanner workers, prompt/evaluation versioning, budget limits, and red-team tests.
