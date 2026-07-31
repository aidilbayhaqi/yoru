# Yoru Platform

Sprint 1 identity foundation untuk Yoru di atas dua aplikasi Next.js, FastAPI
modular monolith, worker, PostgreSQL, Redis, dan Qdrant.

> Versi `0.2.1` memperbaiki bind UUID pada seed migrasi identity. Pengguna
> paket `0.2.0` harus memakai source ini sebelum menjalankan migration
> `20260728_0002`. Lihat `docs/HOTFIX_0.2.1.md`.

## Status

Yang sudah tersedia:

- `apps/storefront` pada port `3000`;
- `apps/console` pada port `3001`;
- `services/api` pada port `8000`;
- `services/worker`;
- Docker Compose untuk PostgreSQL, Redis, Qdrant, API, worker, storefront, dan console;
- environment validation;
- request ID, JSON logs, security headers, CORS allowlist, dan problem details;
- liveness/readiness/startup endpoints;
- Alembic baseline;
- customer register/login dan opaque browser session;
- refresh-token rotation dengan reuse detection;
- logout, logout-all, session revocation, dan active partner selection;
- RBAC capability, tenant context, dan PostgreSQL RLS baseline;
- Argon2id password hashing, CSRF validation, dan login rate limit;
- controlled super-admin bootstrap tanpa public admin registration;
- frontend/backend unit tests;
- GitHub Actions dan Dependabot.

Belum tersedia setelah identity foundation Sprint 1:

- partner onboarding;
- catalog, inventory, order, booking, payment, ledger;
- AI Customer Advisor dan Partner Copilot.
- email verification, account recovery, dan TOTP enrollment UI.

Modul bisnis tersebut baru dimulai setelah foundation gate lulus.

## Struktur

```text
apps/
  storefront/
  console/
packages/
  contracts/
  ui/
services/
  api/
  worker/
docs/
openapi/
scripts/
```

## Prasyarat

- Node.js 24+
- pnpm 11+
- Python 3.12+
- Docker Desktop/Engine dengan Compose

## Menjalankan local

Salin environment:

```bash
cp .env.example .env
```

Install:

```bash
corepack enable
pnpm install
python -m venv .venv
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -e "services/api[dev]" -e "services/worker[dev]"
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "services/api[dev]" -e "services/worker[dev]"
```

Jalankan semua service:

```bash
docker compose up --build
```

Atau hanya infrastructure:

```bash
docker compose up -d postgres redis qdrant
```

Kemudian jalankan frontend, API, dan worker dari terminal terpisah:

```bash
pnpm dev
.venv/bin/uvicorn yoru_api.main:app --app-dir services/api/src --reload --port 8000
.venv/bin/python -m yoru_worker.main
```

## Endpoint awal

| Endpoint              | Tujuan                             |
| --------------------- | ---------------------------------- |
| `GET /`               | Metadata service                   |
| `GET /api/v1/meta`    | Kontrak API foundation             |
| `GET /health/live`    | Process hidup                      |
| `GET /health/ready`   | PostgreSQL, Redis, dan Qdrant siap |
| `GET /health/startup` | Konfigurasi/startup selesai        |
| `GET /docs`           | Swagger UI saat non-production     |

## Quality gate

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build

.venv/bin/ruff check services
.venv/bin/mypy services/api/src services/worker/src
.venv/bin/pytest services/api/tests services/worker/tests
```

Gunakan `make check` pada Linux/macOS setelah `.venv` tersedia.

## Migration

```bash
.venv/bin/alembic -c services/api/alembic.ini upgrade head
```

Migration production harus forward-only dan backward-compatible.

Jika database Sprint 0 sudah berjalan, terapkan migration terbaru:

```bash
docker compose run --rm migrate
docker compose up -d --build
```

Jika migration versi `0.2.0` sebelumnya gagal pada seed `roles.id`, jangan hapus
volume database. Rebuild image dari source `0.2.1`, lalu jalankan kembali:

```bash
docker compose down
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose up -d --build
```

## Authentication Sprint 1

Endpoint tersedia di bawah `/api/v1/auth`:

| Method   | Endpoint          | Tujuan                                   |
| -------- | ----------------- | ---------------------------------------- |
| `POST`   | `/register`       | Self-register customer                   |
| `POST`   | `/login`          | Membuat opaque session                   |
| `POST`   | `/refresh`        | Rotasi access dan refresh token          |
| `GET`    | `/me`             | User, role, tenant, dan capability aktif |
| `PATCH`  | `/active-partner` | Memilih tenant dari membership sendiri   |
| `GET`    | `/sessions`       | Melihat session aktif                    |
| `DELETE` | `/sessions/{id}`  | Mencabut session milik sendiri           |
| `POST`   | `/logout`         | Mencabut session saat ini                |
| `POST`   | `/logout-all`     | Mencabut seluruh session user            |

Admin tidak dapat mendaftar melalui endpoint publik. Setelah migration selesai, buat
super admin dari terminal interaktif:

```bash
docker compose exec api yoru-bootstrap-admin \
  --email admin@your-real-domain.com \
  --name "Yoru Super Admin"
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\bootstrap-admin.ps1 `
  -ProjectRoot "D:\Documents\CODING\Yoru" `
  -Email "admin@your-real-domain.com" `
  -Name "Yoru Super Admin"
```

Password tidak diterima melalui argument command agar tidak masuk shell history.
Gunakan minimal 12 karakter dan sedikitnya tiga kategori karakter.

Request mutation yang memakai session cookie harus mengirim nilai cookie `yoru_csrf`
melalui header `X-CSRF-Token`. Frontend tidak boleh membaca access/refresh token karena
keduanya disimpan sebagai cookie `HttpOnly`.

## Kontrak keamanan

- Browser tidak menjadi sumber authority untuk role, tenant, harga, komisi, atau total.
- CORS menggunakan allowlist eksplisit.
- Secret production tidak boleh berada di `.env` repository.
- Log tidak boleh memuat token, password, OTP, foto, alamat lengkap, atau PII sensitif.
- Endpoint readiness tidak membocorkan credential/hostname internal.
- Session menggunakan secure HttpOnly cookie di production dan refresh rotation.
- Role sensitif sudah ditandai membutuhkan MFA; action sensitif fail-closed sampai
  step-up terverifikasi.
- Authorization menggunakan RBAC + tenant scope + ABAC hook + PostgreSQL RLS.

## Dokumentasi

Lihat folder `docs/` untuk PRD engineering, data model, API, security, AI, testing,
DevOps, roadmap, state machine, dan permission matrix.

Hasil quality gate tersedia di `docs/VALIDATION_REPORT.md` untuk Sprint 0 dan
`docs/VALIDATION_REPORT_SPRINT_1.md` untuk identity foundation.
