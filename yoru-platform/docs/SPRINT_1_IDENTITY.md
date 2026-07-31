# Sprint 1 — Identity and Authorization Foundation

## Scope delivered

- self-registration khusus customer;
- Argon2id password hashing;
- opaque access dan refresh token;
- hash token tersimpan di PostgreSQL, bukan token mentah;
- secure cookie policy per environment;
- refresh rotation dan consumed-token history;
- reuse detection yang merevoke seluruh session family;
- logout, logout-all, dan user-owned session revocation;
- CSRF double-submit validation dan Origin allowlist;
- Redis-backed login rate limit yang fail-closed;
- platform role, partner membership, dan granular permission seed;
- active tenant selection hanya dari membership user;
- application authorization helper untuk capability, tenant, partner status, dan MFA;
- PostgreSQL RLS baseline untuk partner dan membership;
- audit event untuk register, login, logout, session revoke, tenant change, dan replay;
- non-public super-admin bootstrap command.

## Security decisions

### Session

Browser menerima tiga cookie:

| Cookie         | HttpOnly | Path           | Tujuan                          |
| -------------- | -------- | -------------- | ------------------------------- |
| `yoru_access`  | Ya       | `/`            | Opaque access token, TTL pendek |
| `yoru_refresh` | Ya       | `/api/v1/auth` | Opaque refresh token            |
| `yoru_csrf`    | Tidak    | `/`            | Double-submit CSRF token        |

`Secure=true` wajib pada production. Access dan refresh token tidak pernah dikirim
melalui response body atau disimpan pada local storage.

### Registration

Endpoint publik hanya membuat customer. Partner role dan platform role harus berasal
dari controlled onboarding, invitation, atau bootstrap operation yang diaudit.

### Tenant isolation

Authorization dilakukan berlapis:

1. session harus aktif;
2. capability harus diberikan oleh role server-side;
3. `active_partner_id` harus berasal dari membership user;
4. resource `partner_id` harus sama dengan tenant aktif;
5. partner dan membership harus berada dalam state yang mengizinkan tindakan;
6. RLS membatasi query PostgreSQL sebagai defense-in-depth.

### MFA

Schema MFA dan `require_mfa` authorization hook sudah tersedia. Role sensitif ditandai
`requires_mfa=true`. TOTP enrollment, recovery code, dan step-up endpoint tetap
fail-closed dan menjadi bagian lanjutan Sprint 1 sebelum action payout/role mutation
dibuka.

## Integration acceptance

CI menyediakan PostgreSQL dan Redis nyata lalu memeriksa:

- register → session cookie → refresh rotation;
- reuse refresh lama → seluruh family direvoke;
- access token terbaru tidak lagi valid setelah replay terdeteksi;
- partner A dapat memilih tenant A;
- partner A ditolak ketika memilih tenant B;
- query PostgreSQL dengan RLS hanya melihat partner A.

Test integration dilewati secara lokal bila `TEST_DATABASE_URL` dan `TEST_REDIS_URL`
tidak tersedia.

## Remaining identity work

- email verification;
- password recovery yang enumeration-safe;
- TOTP enrollment, confirmation, step-up, dan recovery code;
- controlled partner invitation/onboarding;
- platform UI untuk user/session/role management;
- full browser E2E test;
- external auth/tenant penetration test sebelum production.
