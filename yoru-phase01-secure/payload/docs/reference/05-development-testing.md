# Development & Testing

## 1. Local development target

Sprint 0 harus menyediakan satu command bootstrap dan satu command test. Target developer
experience:

```bash
pnpm install
docker compose up -d
pnpm db:migrate
pnpm db:seed
pnpm dev
```

Root task runner dapat memanggil Python commands, tetapi tidak boleh menyembunyikan error.

## 2. Frontend engineering

### Rendering

- Server Component untuk katalog/detail/read-only secara default.
- Client Component hanya untuk form, interactive filters, cart state, maps, dan tracking.
- Data sensitif tidak diserialisasi ke client component tanpa kebutuhan.
- Mutation melalui typed API client; jangan menaruh secret di Route Handler.

### State

| State                 | Tempat                                       |
| --------------------- | -------------------------------------------- |
| URL filters/sort/page | Search params                                |
| Server data           | Query/cache layer                            |
| Form                  | Form library/local reducer                   |
| Short UI state        | Component state                              |
| Auth capability       | Server session + minimal client context      |
| Cart optimistic view  | Dedicated cart store + server reconciliation |

### Performance rules

- Debounce search 300–500 ms dan cancel stale request.
- Gunakan cursor pagination untuk feed besar.
- Virtualize tabel/list hanya ketika jumlah node terukur besar.
- `useMemo` untuk expensive derived value dengan dependency stabil dan profiling evidence.
- Dynamic import untuk map, heavy editor, dan non-critical chart.
- Image dimension wajib; gunakan responsive image.
- Hindari waterfall; prefetch hanya untuk likely navigation.
- Tetapkan bundle budget per route.

### UX contract

Setiap feature memiliki:

- loading/skeleton;
- empty state;
- recoverable error;
- permission denied;
- offline/retry bila relevan;
- success confirmation;
- destructive confirmation;
- responsive dan keyboard flow;
- readable label, bukan raw UUID.

## 3. Backend engineering

### Layer responsibility

| Layer          | Tanggung jawab                                                |
| -------------- | ------------------------------------------------------------- |
| API            | Parse, auth dependency, map error/response                    |
| Application    | Use case, transaction, authorization call, port orchestration |
| Domain         | Invariant, state transition, policy pure                      |
| Infrastructure | ORM, external provider, cache, queue                          |

### Query rules

- List endpoint selalu memiliki limit maksimum.
- Eager loading dipilih eksplisit untuk mencegah N+1.
- Jangan expose ORM object langsung.
- Bulk job memakai batch dan checkpoint.
- Long provider call tidak menahan DB transaction.
- Cache invalidation setelah commit.
- Advisory/distributed lock harus memiliki scope dan timeout.

### Resilience

- timeout untuk setiap external call;
- retry hanya pada transient/idempotent operation;
- exponential backoff + jitter;
- circuit breaker untuk dependency unstable;
- dead-letter/manual replay untuk job;
- idempotent consumer;
- graceful shutdown.

## 4. Test pyramid

| Level       | Fokus                                              | Target                          |
| ----------- | -------------------------------------------------- | ------------------------------- |
| Unit        | Policy, calculation, state transition, parser      | Cepat dan dominan               |
| Integration | PostgreSQL, Redis, Qdrant, repository, RLS         | Real dependency container       |
| Contract    | OpenAPI, provider adapter/webhook fixtures         | Consumer/provider compatibility |
| Component   | React UI behavior/accessibility                    | Feature states                  |
| E2E         | Critical customer/partner/admin journeys           | Sedikit tetapi high-value       |
| Performance | Search, checkout, webhook burst, dashboard         | Budget/SLO                      |
| Security    | BOLA, auth abuse, upload, SSRF, replay             | Release gate                    |
| AI eval     | Retrieval, safety, grounding, numeric faithfulness | Model/prompt gate               |

## 5. Critical test scenarios

### Auth/tenant

- registration normalization dan duplicate handling;
- login valid/invalid/rate limited;
- refresh rotation dan reuse detection;
- revoke/logout-all;
- customer A tidak dapat melihat order B;
- partner A tidak dapat mengakses resource partner B meski UUID diketahui;
- pool connection tidak membawa RLS context request sebelumnya;
- role downgrade langsung efektif;
- suspended partner write ditolak.

### Commerce

- price berubah setelah cart → quote di-refresh;
- concurrent checkout stock terakhir → hanya satu berhasil;
- duplicate confirm dengan idempotency key → satu order;
- payment redirect tanpa webhook → tidak paid;
- duplicate/out-of-order webhook;
- partial/full refund dan ledger reversal;
- shipment event out-of-order.

### Booking

- overlapping slot ditolak secara concurrent;
- service area invalid;
- professional credential expired;
- cancel/no-show pada setiap cutoff;
- OTP expired/reused;
- tracking hanya actor berhak;
- location retention cleanup.

### Ledger/payout

- debit selalu sama dengan credit;
- komisi rounding;
- refund allocation;
- balance tidak negatif tanpa policy;
- duplicate payout;
- separation of duty;
- reconciliation provider vs ledger.

### AI

- recommendation di luar budget;
- item unpublished/out-of-stock muncul dari stale vector;
- medical diagnosis request;
- prompt injection pada product description;
- cross-tenant retrieval;
- photo tanpa consent;
- raw photo/PII tidak masuk log/vector;
- partner summary angka sama dengan metric snapshot;
- provider timeout menghasilkan fallback.

## 6. CI pipeline

```mermaid
flowchart LR
    Lint["Format/Lint"] --> Type["Type check"]
    Type --> Unit["Unit tests"]
    Unit --> Integration["Integration + migration"]
    Integration --> Contract["OpenAPI/contract"]
    Contract --> Security["Security scans"]
    Security --> Build["Reproducible build"]
    Build --> Preview["Preview environment"]
    Preview --> E2E["Critical E2E"]
```

Required gates:

- formatting;
- ESLint/Ruff;
- TypeScript/mypy or agreed Python type checker;
- unit coverage policy per critical module;
- migration from clean and previous baseline;
- OpenAPI breaking-change diff;
- SAST, dependency, secret, container scan;
- generated client drift check;
- SBOM generation;
- build without uncommitted generated output.

## 7. Test data

- Factory-based; deterministic seed.
- Tidak menggunakan dump production.
- PII sintetik.
- Fixed clock/timezone helpers.
- Provider fixtures ditandatangani dengan test secret.
- Multi-tenant fixtures selalu memiliki minimal partner A dan B.
- AI eval dataset memiliki license/provenance dan version.

## 8. Quality budget

Initial target, harus dikalibrasi dengan load model:

| Metric                            | Target awal                        |
| --------------------------------- | ---------------------------------- |
| Public API availability           | 99.9% bulanan                      |
| Read API p95                      | < 500 ms tanpa provider            |
| Write API p95                     | < 800 ms tanpa provider            |
| Checkout create p95               | < 1.5 s sebelum provider redirect  |
| Auth failure error leakage        | 0                                  |
| Cross-tenant test failure         | 0                                  |
| Ledger imbalance                  | 0                                  |
| Critical/high known vulnerability | 0 saat release                     |
| Storefront LCP p75                | < 2.5 s pada target network/device |
| CLS p75                           | < 0.1                              |

AI latency dan quality memiliki SLO terpisah agar tidak menurunkan core transaction.

## 9. Manual exploratory charters

- customer dengan jaringan lambat melakukan checkout;
- partner mengubah price/stock saat customer checkout;
- professional kehilangan koneksi saat perjalanan;
- admin menangani dispute dan payout bersamaan;
- payment provider mengirim event terlambat;
- AI provider gagal di tengah request;
- user menggunakan bahasa campuran/typo;
- screen reader dan keyboard flow pada login, checkout, booking, dan admin table.
