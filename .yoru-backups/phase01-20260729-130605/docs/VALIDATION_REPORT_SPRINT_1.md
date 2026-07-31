# Sprint 1 Identity Validation Report

Tanggal validasi: 28 Juli 2026  
Versi: 0.2.0

## Quality gate

| Pemeriksaan                 | Hasil                                                          |
| --------------------------- | -------------------------------------------------------------- |
| Prettier                    | Lulus                                                          |
| ESLint                      | Lulus untuk storefront dan console                             |
| TypeScript                  | Lulus untuk 4 workspace package                                |
| Vitest                      | 5 test lulus                                                   |
| Storefront production build | Lulus, 6 route                                                 |
| Console production build    | Lulus, 5 route                                                 |
| Ruff                        | Lulus                                                          |
| mypy strict                 | Lulus untuk 31 source file                                     |
| Pytest lokal                | 26 lulus                                                       |
| Integration test lokal      | 2 dilewati karena PostgreSQL/Redis test service tidak tersedia |
| Alembic offline SQL         | Revision `20260728_0002` berhasil dibuat                       |
| FastAPI runtime smoke       | Liveness, metadata, dan OpenAPI mengembalikan `200`            |
| Readiness fail-closed       | Mengembalikan `503` tanpa dependency                           |
| Implemented auth paths      | 9 path                                                         |
| OpenAPI outline             | 23 path                                                        |
| Compose manifest            | 8 service                                                      |
| Secret pattern scan         | Bersih                                                         |

## Security coverage

Test otomatis memeriksa:

- Argon2id password hash;
- password policy;
- keyed token hash;
- opaque session cookies;
- access dan refresh cookie `HttpOnly`;
- CSRF cookie dapat dibaca frontend tanpa membuka access token;
- Origin allowlist;
- response auth `no-store`;
- Content Security Policy;
- cross-tenant denial;
- suspended partner write denial;
- capability denial;
- MFA step-up fail-closed;
- refresh rotation;
- refresh reuse family revocation;
- identity OpenAPI exposure.

CI menyediakan PostgreSQL dan Redis untuk menjalankan dua acceptance test tambahan:

- refresh replay merevoke seluruh session family;
- tenant isolation dibuktikan pada API dan PostgreSQL RLS.

Acceptance test tersebut belum dijalankan di environment validasi lokal karena Docker
tidak tersedia. Hasil CI atau eksekusi pada workstation Docker tetap menjadi gate
sebelum Sprint 1 dinyatakan siap staging.

## Reproduction

```bash
./scripts/verify.sh
```

Migration:

```bash
docker compose run --rm migrate
```

Full infrastructure:

```bash
docker compose up -d --build
```
