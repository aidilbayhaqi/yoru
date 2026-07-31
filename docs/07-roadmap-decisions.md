# Roadmap, Backlog & Decision Register

## 1. Delivery principles

- Foundation lebih dahulu daripada fitur.
- Vertical slice kecil, dapat diuji, dan dapat dimatikan.
- Tidak ada payment/ledger dummy yang terlihat final.
- Tidak ada AI sebelum source data, consent, safety, dan evaluation siap.
- Setiap sprint menghasilkan working increment dan updated documentation.

Estimasi sprint di bawah adalah urutan logis, bukan komitmen tanggal. Kapasitas tim belum
ditentukan.

## 2. Sprint 0 — Engineering foundation

### Outcomes

- monorepo dan developer tooling;
- local compose;
- FastAPI skeleton + worker;
- Next.js storefront + console skeleton;
- PostgreSQL migration baseline;
- Redis/Qdrant connectivity;
- structured logging, request ID, health/readiness;
- CI quality/security gates;
- generated OpenAPI client workflow.

### Acceptance gate

- clean clone dapat boot dengan documented command;
- CI hijau;
- service tidak start dengan env invalid;
- migration clean/upgrade test lulus;
- no secret committed;
- trace request dapat diikuti API→DB/worker.

## 3. Sprint 1 — Identity and access

### Stories

- customer register/login/logout/recovery;
- partner application identity;
- secure session + refresh rotation;
- partner membership dan active tenant;
- role/permission seed;
- MFA untuk role sensitif;
- audit auth/role;
- admin create/invite flow.

### Acceptance gate

- negative authorization matrix lulus;
- refresh reuse detection lulus;
- tenant A/B isolation lulus;
- admin/finance MFA lulus;
- login enumeration/rate-limit test lulus.

## 4. Sprint 2 — Partner onboarding and verification

- partner profile;
- document upload quarantine/scan;
- verification checklist;
- approve/reject/request revision/block;
- professional registration dan credential;
- service area;
- audit/support view.

## 5. Sprint 3 — Catalog, service, inventory

- category;
- product/variant/media;
- service/duration/price;
- professional skill mapping;
- availability;
- stock/movement/reservation;
- publish moderation;
- public product/service discovery.

## 6. Sprint 4 — Cart, checkout, order, payment

- customer cart;
- quote dan price snapshot;
- stock reservation;
- checkout confirm;
- payment intent;
- verified webhook;
- partner/customer order views;
- cancellation dasar;
- outbox/notification.

## 7. Sprint 5 — Booking and home-service operations

- slot search;
- booking quote/confirm;
- partner/professional acceptance;
- assignment;
- en-route/arrival;
- authorized live tracking;
- OTP check-in/out;
- completion checklist;
- cancellation/no-show.

## 8. Sprint 6 — Ledger, refund, payout, dispute

- double-entry ledger;
- platform commission;
- pending/available balance;
- refund/reversal;
- payout request/approval;
- provider reconciliation;
- dispute/evidence/support flow;
- finance audit/export.

## 9. Sprint 7 — Customer AI Advisor

- consent;
- secure photo pipeline;
- structured need extraction;
- hybrid retrieval/ranking;
- safety gate;
- grounded explanation;
- feedback/evaluation dashboard;
- provider fallback/cost controls.

## 10. Sprint 8 — Partner Copilot

- analytics snapshots;
- deterministic metric tools;
- revenue/inventory/booking narrative;
- evidence-linked recommendations;
- feedback;
- scheduled insight;
- finance-role isolation.

## 11. Sprint 9 — Hardening and launch

- load test;
- external security assessment;
- restore drill;
- accessibility audit;
- data retention jobs;
- provider failover/reconciliation;
- SLO/alerts/runbooks;
- legal/privacy/clinical gate;
- phased pilot.

## 12. Epic backlog

| ID | Epic | Priority | Dependency |
| --- | --- | --- | --- |
| E-001 | Engineering Foundation | P0 | None |
| E-002 | Identity & Session | P0 | E-001 |
| E-003 | Authorization & Tenant Isolation | P0 | E-002 |
| E-004 | Partner Verification | P0 | E-003 |
| E-005 | Catalog & Inventory | P0 | E-004 |
| E-006 | Services & Professionals | P0 | E-004 |
| E-007 | Cart & Quote | P0 | E-005 |
| E-008 | Checkout & Payment | P0 | E-007 |
| E-009 | Product Fulfillment | P0 | E-008 |
| E-010 | Booking & Dispatch | P0 | E-006, E-008 |
| E-011 | Ledger & Payout | P0 | E-008, E-010 |
| E-012 | Dispute & Support | P1 | E-009, E-010 |
| E-013 | Reviews | P1 | E-009, E-010 |
| E-014 | Customer AI Advisor | P1 | E-005, E-006, E-003 |
| E-015 | Partner Copilot | P1 | E-011, analytics |
| E-016 | Advanced Promotion | P2 | Stable commerce |
| E-017 | Automation Actions | P2 | Copilot safety/approval |

## 13. Decision register

Setiap decision memiliki owner, due-before, rationale, dan approval evidence.

| ID | Decision | Recommended baseline | Blocking |
| --- | --- | --- | --- |
| OD-01 | Cross-partner cart | Satu checkout menghasilkan child order per partner; MVP dapat membatasi satu partner per cart untuk menyederhanakan | Checkout |
| OD-02 | Komisi | 10% eligible subtotal setelah partner discount; exclude shipping/tax/tip/gateway fee | Ledger |
| OD-03 | Payment fee | Tampilkan dan alokasikan eksplisit; jangan tersembunyi | Checkout/ledger |
| OD-04 | Payout hold | Hold sampai fulfillment/booking completion + dispute window | Payout |
| OD-05 | Refund allocation | Pro-rata berdasarkan komponen dan funding source | Ledger |
| OD-06 | Booking acceptance | Auto-confirm hanya bila availability dan SLA kuat; selain itu timed partner acceptance | Booking |
| OD-07 | Service area | Radius/zone terverifikasi; hindari free-text | Booking |
| OD-08 | Cancellation/no-show | Tier berdasarkan waktu, actor, perjalanan, dan evidence | Booking/ledger |
| OD-09 | Dental/treatment scope | Non-invasive only pada MVP setelah legal review | Catalog/booking |
| OD-10 | Photo retention | Default ≤24 jam setelah analysis, kecuali user memilih simpan dengan purpose jelas | AI/privacy |
| OD-11 | AI provider | Abstraction + evaluation bake-off berdasarkan safety, quality, privacy, region, cost | AI |
| OD-12 | Data residency/retention | Pilih region/provider setelah legal/privacy review | Infra |
| OD-13 | Logistics | Integrasi provider vs partner-managed delivery | Fulfillment |
| OD-14 | Live tracking | Interval, retention, consent, dan fallback | Booking |
| OD-15 | Review eligibility | Hanya verified transaction; moderation/appeal | Reviews |
| OD-16 | Partner KYC/KYB | Document set, expiry, re-verification, sanctions policy | Onboarding |

## 14. Definition of Ready

Story siap dikerjakan jika:

- actor, intent, acceptance criteria, dan negative path jelas;
- permission dan tenant scope ditentukan;
- state transition ditentukan;
- data/schema/API impact tersedia;
- UX states tersedia;
- observability dan test plan tersedia;
- security/privacy classification tersedia;
- open decision yang blocking telah disetujui.

## 15. Release readiness

Feature siap dirilis jika:

- Definition of Done terpenuhi;
- data migration/backfill selesai;
- support/admin flow tersedia;
- feature flag dan rollback diuji;
- dashboard/alert tersedia;
- product owner menerima acceptance evidence;
- security/privacy owner menerima risk evidence untuk feature sensitif.
