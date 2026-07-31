# Sprint 0 Validation Report

Tanggal validasi: 28 Juli 2026  
Scope: Yoru engineering foundation

## Hasil

| Pemeriksaan              | Hasil                                              |
| ------------------------ | -------------------------------------------------- |
| Prettier                 | Lulus                                              |
| ESLint dan TypeScript    | Lulus untuk 4 workspace package                    |
| Vitest                   | 5 test lulus                                       |
| Next.js production build | Storefront dan console lulus                       |
| Ruff                     | Lulus                                              |
| mypy                     | Lulus untuk 19 source file                         |
| Pytest                   | 12 test lulus                                      |
| Alembic offline SQL      | Baseline migration berhasil dibuat                 |
| API runtime smoke        | `live`, `startup`, dan `meta` mengembalikan `200`  |
| Readiness fail-closed    | Mengembalikan `503` saat dependency tidak tersedia |
| Compose manifest         | 8 service terdeteksi dan terurai                   |
| OpenAPI outline          | Versi 3.x dan 19 path terdeteksi                   |
| Secret pattern scan      | Bersih                                             |

Quality gate dapat direproduksi dengan:

```bash
NEXT_TELEMETRY_DISABLED=1 ./scripts/verify.sh
```

## Batas validasi environment

- Docker tidak tersedia pada environment validasi, sehingga container build dan
  integrasi penuh PostgreSQL, Redis, serta Qdrant belum dijalankan. Manifest Compose
  telah diperiksa secara statis dan CI menjalankan `docker compose config`.
- Next.js production build untuk kedua aplikasi lulus. Runtime `next start` tidak
  dapat dijalankan pada sandbox validasi karena pemanggilan system network interface
  diblokir oleh environment; ini bukan error kompilasi aplikasi.

Integrasi container wajib dijalankan pada workstation atau CI yang memiliki Docker
sebelum Sprint 1 dimulai:

```bash
cp .env.example .env
docker compose config
docker compose up --build
```
