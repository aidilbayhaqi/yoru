# Phase 8 — Partner Copilot

Phase 8 adds tenant-isolated business analytics and a grounded local copilot for verified partners.

## Capabilities

- Current versus previous-period metric snapshots
- Revenue, booking, inventory, finance, and operations insights
- Evidence-backed chat responses using Yoru data only
- Partner feedback and zero-cost local usage tracking
- Weekly digest configuration
- Audit, outbox, RBAC, and PostgreSQL RLS

The initial engine is deterministic (`partner-copilot-local-v1`) and does not call an external model. It is safe to test without an AI provider key. An external provider can later replace the response generator while preserving the endpoint and data contracts.

Enable locally with `FEATURE_PARTNER_COPILOT=true`.
