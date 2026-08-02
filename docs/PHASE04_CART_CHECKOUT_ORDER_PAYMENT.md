# Phase 4 — Cart, Checkout, Order, and Payment

Target release: `0.5.0`  
Alembic revision: `20260801_0005`

## Scope

- Customer-owned single-partner cart.
- Server-side quote and immutable price snapshot.
- Atomic checkout confirmation with inventory row locks.
- Expiring inventory reservations.
- Customer and partner-scoped order views.
- Basic cancellation before fulfillment.
- Idempotency records for checkout and payment intent creation.
- Mock payment intent provider for local integration testing.
- HMAC-SHA256 verified payment webhook with provider-event deduplication.
- Audit and outbox events.
- PostgreSQL RLS for customer and partner access.

## Deliberate boundaries

- Cross-partner cart remains disabled until its product and settlement policy is approved.
- Service booking is Phase 5.
- Refund, ledger, payout, and reconciliation are Phase 6.
- The `mock` provider is not a production payment gateway. Replace it through a provider adapter before launch.

## Local webhook

The default local webhook secret is configured by `PAYMENT_WEBHOOK_SECRET`.
Production startup rejects placeholder secrets.

Example payload:

```json
{
  "provider_event_id": "evt_demo_001",
  "provider_reference": "mock_pi_...",
  "status": "succeeded",
  "occurred_at": "2026-08-01T05:00:00Z"
}
```

Compute `X-Yoru-Signature` as lowercase hex HMAC-SHA256 over the raw request body.
