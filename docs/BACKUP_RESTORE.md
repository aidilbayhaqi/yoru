# Backup and Restore Drill

- Keep encrypted backups outside the application host.
- Record backup timestamp, SHA-256, database version, retention class, and operator.
- Test restoration at least every 30 days.
- Restore into an isolated drill database, never over the active production database.
- Verify `alembic_version`, critical table counts, and representative data.
- Drop the drill database after verification.
- Record the outcome through `POST /api/v1/platform/ops/restore-drills`.

A backup that has never been restored is not a verified backup.
