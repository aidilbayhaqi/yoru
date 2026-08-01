# Yoru Phase 2 Patch — Partner Onboarding

This incremental patch upgrades the Phase 0+1 baseline from `0.2.1` to `0.3.0`.

## Included

- Partner application profile and owner membership bootstrap
- Partner verification state machine
- Service-area validation
- Document quarantine metadata and scan-result command
- Platform review, verify, revision, reject, suspend, and reinstate commands
- Audit/outbox events
- Tenant RLS and permission seeds
- Alembic migration `20260731_0003`
- Backend unit tests and implementation notes

## Apply

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\yoru-phase02-partner-onboarding\apply-phase.ps1 `
  -ProjectRoot D:\Documents\CODING\YoruService
```

The installer verifies the current release, validates payload hashes, backs up changed files,
applies the payload, verifies installed hashes, and updates `.yoru-release.json` only after a
successful copy. A failed copy is rolled back.

## Migrate and validate

```powershell
cd D:\Documents\CODING\YoruService
docker compose build --no-cache migrate api worker
docker compose run --rm migrate
docker compose run --rm api pytest
docker compose up -d --build
docker compose ps
```

Do not run `docker compose down -v` for this update.

## Known boundary

The patch creates secure document metadata and quarantine keys, but it does not fake binary
upload or malware scanning. A real object-storage adapter and scanner worker remain the next
integration milestone.
