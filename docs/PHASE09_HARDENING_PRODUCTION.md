# Phase 9 — Hardening and Production Launch

Release target: **Yoru 1.0.0**  
Alembic target: **20260802_0010**

This phase adds production release controls rather than new marketplace behavior:

- request timeout and request-size enforcement;
- hardened response headers and hidden server banner;
- protected Prometheus-compatible metrics endpoint;
- production-only configuration validation;
- platform operations and security-event registers;
- retention execution and auditable job history;
- backup/restore drill recording;
- launch-gate evaluation;
- Docker production override, TLS reverse-proxy example, smoke/preflight/load scripts;
- production, backup, and incident-response runbooks.

## Important boundary

The installer makes the codebase production-capable, but it cannot certify the actual host,
network, DNS, TLS, cloud account, payment provider, malware scanner, object storage,
external penetration test, or legal/privacy approval. Those remain launch gates and must
be verified in the deployment environment.
