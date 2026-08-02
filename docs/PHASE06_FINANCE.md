# Phase 6 — Ledger, Refund, Payout, Reconciliation, and Dispute

Phase 6 adds a double-entry ledger and partner settlement lifecycle. A verified
payment automatically creates a sale journal, commission entry, settlement,
and pending partner balance. Platform finance can release settlements after the
hold period. Customer refunds, partner payouts, disputes, evidence metadata,
and provider reconciliation are modeled with explicit states, audit events,
outbox events, permissions, and PostgreSQL RLS.

Amounts are stored in currency minor units. The default commission is 10% and
the default settlement hold is seven days. Provider execution is represented by
platform-only completion endpoints using the local mock provider. Replace these
with signed provider webhooks before production launch.
