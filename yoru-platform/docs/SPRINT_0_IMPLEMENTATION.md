# Sprint 0 Implementation

## Scope delivered

- pnpm workspace;
- Next.js storefront and console;
- shared contracts and UI package;
- FastAPI application factory;
- environment validation;
- request ID and JSON request logs;
- security headers and explicit CORS allowlist;
- liveness, readiness, and startup endpoints;
- PostgreSQL async engine;
- Redis and Qdrant readiness checks;
- Alembic baseline with metadata, outbox, and audit tables;
- worker infrastructure probe and lifecycle;
- Docker Compose;
- frontend and backend tests;
- CI, Dependabot, and secret scanning;
- Windows PowerShell and POSIX developer scripts.

## Explicitly deferred

- authentication/session;
- RBAC, ABAC, tenant scope, and RLS;
- domain tables;
- business workflows;
- provider integrations;
- AI.

## Foundation exit criteria

| Gate                     | Evidence                          |
| ------------------------ | --------------------------------- |
| Environment fails closed | Settings tests                    |
| API process observable   | JSON logs + request ID            |
| Dependency readiness     | PostgreSQL/Redis/Qdrant checks    |
| Schema versioned         | Alembic baseline                  |
| Web apps compile         | Next.js production builds         |
| Code quality             | ESLint, TypeScript, Ruff, mypy    |
| Regression protection    | Vitest and Pytest                 |
| Supply-chain baseline    | Lockfile, Dependabot, secret scan |

## Next sprint

Sprint 1 starts with identity and authorization:

1. user and credential schema;
2. secure browser session and refresh rotation;
3. partner membership;
4. RBAC capabilities;
5. ABAC/tenant policy;
6. PostgreSQL RLS;
7. MFA for sensitive roles;
8. negative authorization tests;
9. auth audit events.
