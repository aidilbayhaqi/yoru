# DevOps & Observability

## 1. Environments

| Environment | Tujuan                     | Data                 |
| ----------- | -------------------------- | -------------------- |
| Local       | Development cepat          | Synthetic seed       |
| CI          | Automated verification     | Ephemeral            |
| Preview     | Per-PR review              | Synthetic/minimized  |
| Staging     | Production-like validation | Synthetic/anonymized |
| Production  | Customer traffic           | Real, restricted     |

Tidak ada shared secret atau database antara staging dan production.

## 2. Deployment units

- `storefront`: stateless Next.js deployment;
- `console`: stateless Next.js deployment;
- `api`: stateless FastAPI replicas;
- `worker`: separately scalable;
- managed/self-hosted PostgreSQL, Redis, Qdrant, object storage sesuai keputusan infra;
- migration job dijalankan terkontrol sebelum/selama compatible rollout.

## 3. Release strategy

1. CI membuat immutable artifact dan SBOM.
2. Deploy ke preview/staging.
3. Jalankan migration yang backward-compatible.
4. Smoke test + critical E2E.
5. Progressive/canary rollout bila platform memungkinkan.
6. Pantau error, latency, saturation, dan business invariant.
7. Promote atau rollback aplikasi.
8. Contract migration dilakukan pada release terpisah.

Feature berisiko memakai feature flag dengan owner, expiry, dan cleanup task.

## 4. Health endpoints

| Endpoint          | Meaning                                           |
| ----------------- | ------------------------------------------------- |
| `/health/live`    | Process hidup; tidak memanggil dependency         |
| `/health/ready`   | Siap menerima traffic; dependency kritis tersedia |
| `/health/startup` | Initialization/migration compatibility selesai    |

Response tidak membocorkan credential, host internal, atau versi detail sensitif.

## 5. Observability

### Logs

Structured JSON dengan request/trace ID, service, route template, status, latency,
sanitized actor/tenant identifiers, dan error code.

### Metrics

Platform:

- request rate/error/latency;
- DB pool saturation, query latency, deadlock;
- Redis hit/miss/memory/eviction;
- queue depth/oldest age/retry/DLQ;
- Qdrant query latency/filter result count;
- provider latency/error/circuit state;
- cache invalidation failure.

Business invariants:

- checkout created/failed;
- payment pending too long;
- webhook lag;
- stock reservation expired;
- booking assignment lag;
- booking overlap rejection;
- ledger imbalance (harus nol);
- payout reconciliation mismatch;
- AI unsafe/fallback/schema failure;
- cross-tenant policy denial anomaly.

### Traces

Trace mencakup:

- Next.js server request;
- API handler dan use case;
- DB/Redis/Qdrant span;
- worker/outbox;
- provider call.

Jangan memasukkan prompt/foto/PII ke span attributes.

## 6. SLO and alerting

Alert berdasarkan user impact dan burn rate, bukan setiap error tunggal.

| Signal       | Alert example                             |
| ------------ | ----------------------------------------- |
| Availability | Multi-window error budget burn            |
| Checkout     | Success rate turun signifikan             |
| Payment      | Verified webhook lag melewati threshold   |
| Booking      | Assignment queue age tinggi               |
| Ledger       | Imbalance > 0 langsung page               |
| Auth         | Spike login failure/token reuse           |
| Security     | Cross-tenant denial anomaly/export spike  |
| AI           | Safety gate failure/provider cost anomaly |

Setiap alert memiliki runbook, owner, severity, dan expected action.

## 7. Backup and recovery

- PostgreSQL PITR + encrypted backup.
- Object storage versioning/retention sesuai class.
- Qdrant snapshot, tetapi dapat direbuild dari canonical source.
- Redis tidak menjadi satu-satunya copy.
- Config dan IaC versioned.
- Restore drill berkala.

Initial recovery targets yang perlu disetujui:

| System                    | RPO                       | RTO        |
| ------------------------- | ------------------------- | ---------- |
| Transaction database      | ≤ 5 menit                 | ≤ 60 menit |
| Object storage restricted | ≤ 15 menit                | ≤ 4 jam    |
| Qdrant                    | Rebuild/snapshot ≤ 24 jam | ≤ 8 jam    |
| Analytics/read models     | Rebuildable               | ≤ 24 jam   |

## 8. Capacity planning

Track:

- orders/bookings/day and peak RPS;
- active partners/professionals;
- product variants;
- location updates/minute;
- webhook burst;
- vector count/dimension/payload indexes;
- AI requests/token/image/day;
- audit/ledger growth.

Load test harus menggunakan model traffic, bukan hanya endpoint tunggal.

## 9. Incident response

Severity:

- SEV-1: data breach, payment/ledger corruption, broad outage.
- SEV-2: checkout/booking unavailable, major provider failure.
- SEV-3: degraded non-critical feature/AI.

Flow:

1. detect dan declare;
2. assign incident commander;
3. contain/disable feature/provider;
4. preserve evidence;
5. recover/reconcile;
6. communicate sesuai policy;
7. blameless post-incident review;
8. track corrective actions.

Break-glass access short-lived, MFA, approved, dan fully audited.

## 10. Production readiness checklist

- [ ] Environment config divalidasi.
- [ ] Secret manager dan rotation siap.
- [ ] Migration/rollback plan siap.
- [ ] Dashboard dan alerts aktif.
- [ ] Backup restore telah diuji.
- [ ] Provider webhook dan reconciliation diuji.
- [ ] Runbook auth/payment/booking/ledger/AI tersedia.
- [ ] Load/security test lulus.
- [ ] Legal/privacy gates disetujui.
- [ ] On-call ownership jelas.
