# Contributing to Yoru

Dokumen ini mendefinisikan workflow tim ketika source code mulai dibuat.

## Branch dan perubahan

- Branch utama: `main`, selalu deployable.
- Gunakan branch singkat: `feat/`, `fix/`, `chore/`, `docs/`, `security/`.
- Satu pull request menangani satu tujuan yang dapat direview.
- Jangan mencampur refactor besar dengan fitur bisnis.
- Perubahan schema, permission, state machine, komisi, dan AI tool wajib menyertakan ADR
  atau pembaruan decision register.

## Commit

Gunakan Conventional Commits:

```text
feat(auth): add rotating refresh token
fix(booking): reject overlapping professional schedule
security(api): enforce partner scope on order detail
docs(adr): record commission calculation decision
```

## Pull request checklist

- [ ] Acceptance criteria tercapai.
- [ ] Lint, formatting, type-check, unit, integration, dan contract test lulus.
- [ ] Migrasi upgrade dan downgrade/dev rollback diuji.
- [ ] Authorization negative test tersedia.
- [ ] Query baru diperiksa dengan `EXPLAIN (ANALYZE, BUFFERS)` bila kritis.
- [ ] Tidak ada secret, PII, token, atau foto sensitif di diff/log/fixture.
- [ ] API dan generated client tetap sinkron.
- [ ] Error state, loading state, empty state, dan accessibility diuji.
- [ ] Observability ditambahkan untuk flow baru.
- [ ] Dokumentasi dan feature flag diperbarui.

## Review ownership

| Perubahan | Reviewer wajib |
| --- | --- |
| Auth, permission, tenant scope | Backend + security owner |
| Payment, ledger, payout | Backend + finance/product owner |
| Migration atau index | Backend + database owner |
| AI prompt/tool/retrieval | AI owner + domain/product owner |
| UI shared component | Frontend owner |
| CI/deployment/secret | Platform owner |

## Coding standards

### TypeScript/Next.js

- TypeScript strict; hindari `any`.
- Server Component secara default; Client Component hanya saat interaktivitas dibutuhkan.
- Validasi respons API pada boundary.
- Pisahkan server state, form state, dan local UI state.
- Gunakan shared API client; jangan membuat `fetch` tersebar tanpa policy.
- `useMemo`/`useCallback` harus memiliki alasan terukur, bukan default.
- Batalkan request search lama menggunakan `AbortController`.
- Jangan render HTML dari partner/customer tanpa sanitization.

### Python/FastAPI

- Type hint wajib untuk public function.
- Router hanya menangani HTTP concern; business rule berada di application/domain service.
- Repository tidak mengandung authorization decision.
- Pydantic schema terpisah dari ORM model.
- Semua I/O async harus benar-benar non-blocking.
- Transaction boundary eksplisit.
- Tidak ada broad `except Exception` tanpa re-raise/structured handling.
- Money menggunakan integer minor unit, bukan float.
- Waktu disimpan dalam UTC.

### Database

- Migration forward-only di production.
- Foreign key dan constraint diberi nama konsisten.
- Tenant-owned row wajib memiliki `partner_id NOT NULL`.
- Unique constraint tenant-aware.
- Soft delete hanya bila ada kebutuhan audit/restore yang jelas.
- Ledger dan audit log append-only.
- Index baru wajib memiliki query owner dan alasan.

## Definition of Done

Sebuah story selesai hanya jika:

1. fungsi dan negative path lulus;
2. authorization dan tenant isolation teruji;
3. observability memadai;
4. dokumentasi diperbarui;
5. migration aman;
6. tidak ada critical/high security finding;
7. accessibility dan performance budget tidak turun tanpa persetujuan;
8. feature dapat dimatikan atau di-rollback dengan aman.
