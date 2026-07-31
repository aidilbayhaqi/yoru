# Yoru Phase Update Workflow

Phase 0 dan Phase 1 digabung sebagai baseline `phase-01` versi `0.2.1`.
Baseline dipasang melalui `apply-full-source.ps1` yang tersedia di paket
`yoru-phase01-secure`.

## Instalasi baseline

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\yoru-phase01-secure\apply-full-source.ps1 `
  -ProjectRoot D:\Documents\CODING\YoruService
```

Installer mempertahankan `.env`, `.git`, dan Docker named volume. File lama yang
ditimpa disalin ke `.yoru-backups` di dalam project root.

Setelah installer selesai:

```powershell
cd D:\Documents\CODING\YoruService

docker compose down
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose up -d --build
docker compose ps
```

## Format Phase 2 dan seterusnya

Setiap phase berikutnya berupa patch yang hanya berisi file baru atau berubah:

```text
yoru-phaseNN-<nama>/
  apply-phase.ps1
  manifest.sha256
  payload/
  removed-files.txt
```

`apply-phase.ps1` wajib:

- memeriksa versi awal pada `.yoru-release.json`;
- menolak patch jika baseline tidak sesuai;
- membuat backup file yang berubah;
- menyalin payload dan memproses daftar penghapusan secara terbatas;
- memverifikasi checksum;
- memperbarui release marker hanya setelah seluruh proses berhasil;
- melakukan rollback file ketika penerapan gagal.

## Aturan tetap

- port API tetap `8000` kecuali ada perubahan eksplisit;
- `.env` dan Docker named volume tidak dimasukkan ke ZIP;
- jangan menjalankan `docker compose down -v` untuk update biasa;
- migration Alembic harus tetap berantai dan menjaga data phase sebelumnya.
