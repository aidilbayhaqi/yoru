# Yoru feature status — Phase 9 hardening

Status vocabulary:

- `mock`: visual-only or local browser state.
- `api-ready`: backend contract exists and is tested.
- `integrated`: frontend calls the real API and handles loading/error/empty states.
- `production-gated`: integrated, but an operational or policy gate remains.
- `production-ready`: load, security, backup/restore, observability, and runbook gates passed.

| Capability                                | Status           | Notes / remaining gate                                                                                                                 |
| ----------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Customer register and login               | integrated       | Stable field-level 422 contract, request ID, local validation, refresh single-flight.                                                  |
| Partner product catalog                   | integrated       | Draft/edit/media registration/review submission/archive connected to API. Object storage upload itself remains a separate integration. |
| Partner inventory                         | integrated       | Uses optimistic `expected_version`; conflict is surfaced to the operator.                                                              |
| Product moderation                        | integrated       | Superadmin queue and publish/revision/reject decisions connected to API.                                                               |
| Booking lifecycle API                     | api-ready        | Existing transactional lifecycle remains the source of truth.                                                                          |
| Booking maintenance                       | production-gated | Tracking/OTP cleanup enabled. Automatic cancel/no-show is implemented but disabled by default pending business policy approval.        |
| Worker retries and DLQ                    | integrated       | Bounded exponential retry and Redis dead-letter list. Add alerting/consumer runbook before production.                                 |
| Dashboard metrics, orders, finance, audit | mock             | Existing demo widgets must not be labelled live until their API queries replace fixture data.                                          |
| AI advisor / partner copilot              | api-ready        | Keep all outputs advisory; no direct mutation of financial or lifecycle truth.                                                         |

## Release rule

A feature may only move to `production-ready` when its tests, observability, failure handling, permissions, data migration, rollback, and operating runbook are all present.
