# Yoru Sprint 1 Hotfix 0.2.1

Tanggal: 29 Juli 2026

## Masalah

Migrasi Alembic `20260728_0002_identity_authorization` gagal saat melakukan seed
role pada PostgreSQL:

```text
column "id" is of type uuid but expression is of type character varying
```

Nilai UUID dikirim sebagai Python `str`, sehingga dialect `asyncpg` mengompilasi
parameter menjadi `VARCHAR`. Masalah yang sama juga terdapat pada seed permission
dan akan muncul setelah seed role berhasil.

## Perbaikan

- seed role dan permission sekarang memakai `uuid.UUID`;
- bind parameter memakai `postgresql.UUID(as_uuid=True)` secara eksplisit;
- regression test memverifikasi SQL untuk dialect `asyncpg` menghasilkan parameter
  `::UUID`;
- migrasi tetap memakai revision ID yang sama karena revision tersebut belum pernah
  berhasil diterapkan pada database terdampak.

## Menjalankan hotfix

Jalankan dari root proyek menggunakan PowerShell:

```powershell
docker compose down
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose up -d --build
docker compose ps
docker compose exec api alembic -c alembic.ini current
```

Revision yang diharapkan:

```text
20260728_0002 (head)
```

Tidak perlu menjalankan `docker compose down -v`. PostgreSQL menggunakan
transactional DDL, sehingga kegagalan migrasi sebelumnya membatalkan perubahan
revision `0002` dan volume database dapat dipertahankan.

## Validasi

Validasi yang dijalankan pada source hotfix:

- Ruff: lulus;
- Mypy strict: lulus;
- Pytest: 28 lulus, 2 integration test dilewati karena PostgreSQL/Redis tidak
  tersedia di runtime validasi;
- regression test bind UUID: 2 lulus;
- Alembic offline SQL: lulus, 8 seed role dan 17 seed permission;
- Prettier, ESLint, TypeScript: lulus;
- Vitest: 5 lulus;
- production build Next.js storefront dan console: lulus.

Docker Engine tidak tersedia di runtime validasi. Eksekusi migration PostgreSQL
nyata harus dikonfirmasi melalui perintah di atas pada Docker Desktop pengguna.
