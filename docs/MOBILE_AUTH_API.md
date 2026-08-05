# Yoru Backend P0 — Mobile Authentication

This patch keeps the existing browser authentication flow intact and adds a native-mobile transport for Flutter.

## Implemented

- `POST /api/v1/mobile/auth/register`
- `POST /api/v1/mobile/auth/login`
- `POST /api/v1/mobile/auth/refresh`
- `GET /api/v1/mobile/auth/me`
- `POST /api/v1/mobile/auth/logout`
- `POST /api/v1/mobile/auth/logout-all`
- `Authorization: Bearer <access_token>` support on existing protected APIs
- Browser cookie sessions still require CSRF tokens
- Mobile responses use `Cache-Control: no-store`
- Unit/router tests for the new transport

## Apply

```bash
python apply_p0_mobile_auth.py /path/to/yoru
```

Run quality gates from the repository root:

```bash
.venv/bin/ruff check services/api/src services/api/tests
.venv/bin/mypy services/api/src
.venv/bin/pytest services/api/tests/test_identity_router.py \
  services/api/tests/test_mobile_auth_router.py
```

## Flutter contract

Login response shape:

```json
{
  "token_type": "Bearer",
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 900,
  "refresh_expires_in": 2592000,
  "session": {
    "user": {},
    "active_partner_id": null,
    "platform_roles": [],
    "permissions": [],
    "memberships": []
  }
}
```

Flutter stores both tokens in secure storage. API requests send the access token in the `Authorization` header. A `401` should trigger one serialized refresh attempt, then retry the original request once.
