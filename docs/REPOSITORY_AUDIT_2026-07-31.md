# Yoru Repository Audit — 31 July 2026

## Documents reviewed

- `README.md`
- `PHASE_UPDATE.md`
- `docs/00-engineering-overview.md`
- `docs/01-domain-data-model.md`
- `docs/02-api-contract.md`
- `docs/03-auth-security.md`
- `docs/07-roadmap-decisions.md`
- `docs/08-status-permissions.md`
- `docs/SPRINT_1_IDENTITY.md`
- `docs/VALIDATION_REPORT_SPRINT_1.md`
- API identity models, permissions, repository, router, service, migrations, and tests

## Baseline assessment

The repository has a credible Phase 0+1 engineering baseline rather than a UI-only prototype.
The strongest completed areas are environment validation, FastAPI/Next.js service boundaries,
PostgreSQL migrations, cookie-based sessions, refresh rotation, tenant membership, role and
permission seeds, row-level security, audit events, health checks, tests, and CI quality gates.

The domain roadmap correctly places partner verification before catalog, inventory, order,
booking, payment, ledger, and AI work. The API contract and status document already define the
partner endpoints and the expected verification lifecycle, but the source previously contained
only the minimal `partners` identity table and no partner-onboarding module.

## Gap selected for implementation

Phase 2 starts with one testable backend vertical slice:

1. create a partner application and owner membership;
2. complete profile, document metadata, and service area;
3. submit only after required documents are recorded as clean;
4. review with explicit state transitions;
5. verify, request revision, reject, suspend, or reinstate;
6. preserve tenant isolation, MFA requirements, auditability, and outbox integration.

This is the correct dependency for Sprint 3 because later catalog and service publication already
assume that only verified partners may perform business writes.

## Changes in version 0.3.0

- New `partners` module with router, schemas, service, repository, models, and state machine.
- Extended partner aggregate fields while retaining the existing identity model.
- New `partner_verifications`, `partner_documents`, and `service_areas` tables.
- New permissions for document and service-area writes and scan-result recording.
- RLS policies for partner application creation and all new tenant resources.
- Alembic chain advanced from `20260728_0002` to `20260731_0003`.
- API version advanced from `0.2.1` to `0.3.0`.
- Unit coverage for state transitions, area validation, scan-state validation, and submission gates.

## Remaining Phase 2 priorities

1. Real object storage with short-lived signed upload URLs.
2. Worker-driven malware scanning with retries and dead-letter handling.
3. Professional registration and credential expiry lifecycle.
4. Partner and verifier console screens with browser E2E tests.
5. PostgreSQL integration tests for the complete RLS authorization matrix.
6. Document-expiry and re-verification scheduled jobs.
7. TOTP enrollment/challenge UI required for operational verifier workflows.

## Recommended release gate

Do not merge to a production branch until all of the following pass against a clean copy of the
real repository:

- patch checksum and rollback test on Windows PowerShell;
- Docker image rebuild;
- Alembic upgrade from `20260728_0002` and downgrade rehearsal on disposable data;
- full API unit suite;
- PostgreSQL/Redis integration suite;
- tenant A/B negative-access tests;
- verifier recent-MFA positive and negative tests;
- generated OpenAPI diff review.
