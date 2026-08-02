# Phase 5 — Booking and Home-Service Operations

Yoru `0.6.0` adds the operational service lifecycle on top of the published
service catalog from Phase 3 and commerce foundation from Phase 4.

## Included

- customer address book and immutable address snapshot on booking;
- capacity-aware booking creation using `service_availability`;
- lifecycle: requested, confirmed, assigned, on-the-way, arrived, in-progress,
  completed, cancelled, and no-show;
- professional assignment with schedule-conflict protection;
- customer-issued check-in and check-out OTP with attempt limits and expiry;
- completion checklist and notes;
- explicit customer consent for live tracking;
- tracking session TTL and location ping history;
- audit and outbox events;
- partner/customer/platform PostgreSQL RLS;
- incremental Alembic migration `20260801_0006`.

## Live tracking

Tracking endpoints are protected by the existing feature flag. Enable locally:

```env
FEATURE_LIVE_TRACKING=true
```

Location sharing requires explicit customer consent and is automatically stopped
when service completes or booking is cancelled.

## Release boundary

This phase intentionally does not implement dispatch optimization, push
notifications, route-provider integration, or background expiry workers. Those
are later operational/hardening tasks.
