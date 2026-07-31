# Yoru Phase 0+1 Secure Baseline

Paket ini menyatukan:

- Phase 0: monorepo, Next.js storefront/console, FastAPI, worker, PostgreSQL,
  Redis, Qdrant, Docker Compose, Alembic baseline, health check, logging, dan CI;
- Phase 1: authentication, secure browser session, refresh rotation, CSRF,
  rate limit, RBAC, partner membership, PostgreSQL RLS, dan audit foundation;
- hotfix `0.2.1`: UUID seed role dan permission untuk dialect `asyncpg`.

## Struktur paket

```text
yoru-phase01-secure/
  apply-full-source.ps1
  manifest.sha256
  payload/
```

`payload/` tidak berisi `.env`, dependency, cache, atau build output.

## Menjalankan installer

Ekstrak ZIP di folder tempat Anda ingin menyimpan paket installer, kemudian:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\yoru-phase01-secure\apply-full-source.ps1 `
  -ProjectRoot D:\Documents\CODING\YoruService
```

Installer akan:

1. memvalidasi struktur payload;
2. membuat project root apabila belum tersedia;
3. membuat backup untuk setiap file lama yang akan ditimpa;
4. menyalin full source Phase 0+1;
5. memverifikasi checksum setiap file;
6. memastikan versi `0.2.1` dan hotfix migration terpasang.

File `.env`, `.git`, dan Docker named volume tidak dihapus atau ditimpa.

## Menjalankan aplikasi

```powershell
cd D:\Documents\CODING\YoruService

docker compose down
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose up -d --build
docker compose ps
```

Verifikasi versi dan migration:

```powershell
docker compose run --rm --no-deps migrate `
  python -c "import yoru_api; print(yoru_api.__version__)"

docker compose exec api alembic -c alembic.ini current
```

Hasil yang diharapkan:

```text
0.2.1
20260728_0002 (head)
```

Jangan menggunakan `docker compose down -v` untuk update biasa.

## Format phase berikutnya

Phase 2 dan seterusnya menggunakan patch kumulatif:

```text
yoru-phase02-<nama>/
  apply-phase.ps1
  manifest.sha256
  payload/
  removed-files.txt
```

Patch hanya membawa file baru atau berubah. Installer patch akan memeriksa
`.yoru-release.json`, membuat backup, menerapkan perubahan, memverifikasi
checksum, dan memperbarui release marker.
