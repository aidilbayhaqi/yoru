# Yoru Production Runbook

## Required launch sequence

1. Install every phase through v1.0.0 and migrate to `20260802_0010`.
2. Create production secrets and never commit the resulting `.env`.
3. Deploy behind TLS using explicit trusted hosts and HTTPS CORS origins.
4. Run `scripts/preflight-production.ps1`.
5. Create a database backup and execute `scripts/restore-drill.ps1`.
6. Record the successful restore drill through the Operations API.
7. Run smoke and load tests against the staging environment.
8. Resolve all critical security events.
9. Evaluate the launch gate. Launch only when the result is `pass`.
10. Use a phased rollout and monitor errors, latency, payments, bookings, and ledger integrity.

## Deployment command example

```powershell
$env:COMPOSE_FILE="compose.yaml;deploy/docker-compose.production.yml"
docker compose --env-file .env.production up -d --build
```

Adjust the base compose filename to match the repository.

## Metrics

The metrics endpoint is `/api/v1/metrics` and requires either:

- `Authorization: Bearer <METRICS_TOKEN>`, or
- `X-Ops-Token: <METRICS_TOKEN>`.

The in-process registry is suitable for a single replica and baseline scraping. For multiple
replicas, scrape each replica or replace it with OpenTelemetry/Prometheus client integration.

## Rollback policy

Source rollback is acceptable before production traffic. After orders, payments, ledger entries,
bookings, payouts, or AI data have been written under v1.0.0, prefer a forward fix. A database
downgrade can destroy operational records and must never be run casually.
