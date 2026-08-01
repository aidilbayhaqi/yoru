# Sprint 2 — Partner Onboarding & Verification

Version: `0.3.0`  
Alembic head: `20260731_0003`

## Scope delivered

This increment implements the first complete backend vertical slice for partner onboarding:

- authenticated partner application creation;
- automatic `partner_owner` membership creation;
- editable profile in `draft` and `revision_required` states;
- service areas using validated radius or postal-code zones;
- private document metadata registered into a quarantine namespace;
- explicit clean/infected/error scan result recording;
- submission completeness checks;
- platform review queue;
- start review, request revision, verify, reject, suspend, and reinstate commands;
- tenant RLS, platform permission checks, CSRF checks, recent-MFA checks for sensitive review commands;
- audit events and outbox events for material state transitions.

## State machine

```text
draft -> submitted -> under_review -> verified
                              |-----> revision_required -> submitted
                              |-----> rejected
verified -> suspended -> verified
verified -> closed (reserved; no endpoint in this increment)
```

Only a `verified` partner can pass the existing business-write guard used by later catalog,
order, and booking modules.

## API endpoints

### Partner

- `POST /api/v1/partners`
- `GET /api/v1/partners/{partner_id}`
- `PATCH /api/v1/partners/{partner_id}`
- `POST /api/v1/partners/{partner_id}/service-areas`
- `DELETE /api/v1/partners/{partner_id}/service-areas/{service_area_id}`
- `POST /api/v1/partners/{partner_id}/documents`
- `POST /api/v1/partners/{partner_id}/submit`

### Platform review

- `GET /api/v1/admin/partners?status=submitted`
- `POST /api/v1/admin/partner-documents/{document_id}/scan-result`
- `POST /api/v1/admin/partners/{partner_id}/review/start`
- `POST /api/v1/admin/partners/{partner_id}/verify`
- `POST /api/v1/admin/partners/{partner_id}/block`
- `POST /api/v1/admin/partners/{partner_id}/reinstate`

All state-changing browser requests require the current `X-CSRF-Token` header.
Platform scan/review/block commands require a recent MFA verification in the active session.

## Submission gate

An application can be submitted only when:

1. required profile fields are present;
2. at least one service area exists;
3. `business_registration` and `owner_identity` document records have `scan_status=clean`.

## Important boundary

This phase records document metadata and a quarantine object key. It deliberately does **not**
pretend to upload or virus-scan binary files. The next storage integration must generate a
short-lived signed upload URL, receive provider completion events, run a real malware scanner,
and call the scan-result command from a trusted worker/service identity.

## Apply and validate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\yoru-phase02-partner-onboarding\apply-phase.ps1 `
  -ProjectRoot D:\Documents\CODING\YoruService
```

Then:

```powershell
cd D:\Documents\CODING\YoruService
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose run --rm api pytest
docker compose up -d --build
docker compose ps
```

Do not use `docker compose down -v` during this update.

## Deferred Sprint 2 work

- real object-storage signed upload adapter;
- asynchronous malware scanner worker and retry/dead-letter flow;
- professional registration and credential lifecycle;
- console UI and browser E2E coverage;
- cursor pagination for the review queue;
- document expiry/re-verification scheduled job;
- penetration test and PostgreSQL integration/RLS test matrix in CI.
