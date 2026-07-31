# API Contract

## 1. General rules

| Concern | Contract |
| --- | --- |
| Base URL | `/api/v1` |
| Serialization | JSON, snake_case |
| Error | RFC 9457-style `application/problem+json` |
| Time | ISO 8601 UTC |
| Money | `amount_minor` + `currency` |
| ID | Opaque string/UUID; UI tidak menonjolkan raw ID |
| Auth | Secure HttpOnly cookies; CSRF untuk state-changing browser request |
| Correlation | `X-Request-ID` diterima/dibuat server |
| Idempotency | `Idempotency-Key` untuk checkout, payment, refund, payout, booking command |
| Versioning | Major path version; additive change di versi aktif |
| Deprecation | Header + changelog + migration window |

## 2. Resource response

```json
{
  "data": {
    "id": "opaque-id",
    "type": "product",
    "attributes": {}
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

List dengan cursor:

```json
{
  "data": [],
  "page": {
    "next_cursor": "opaque-signed-cursor",
    "has_more": false
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

Cursor harus opaque, signed, scoped ke filter/sort, dan memiliki batas umur.

## 3. Error contract

```json
{
  "type": "https://docs.yoru.id/errors/booking-slot-unavailable",
  "title": "Booking slot is unavailable",
  "status": 409,
  "code": "BOOKING_SLOT_UNAVAILABLE",
  "detail": "The selected professional is no longer available.",
  "instance": "/api/v1/bookings",
  "request_id": "req_...",
  "errors": [
    {
      "field": "scheduled_start",
      "code": "conflict",
      "message": "Choose another time."
    }
  ]
}
```

Jangan mengirim stack trace, SQL, provider secret, internal hostname, atau policy detail.

| Status | Penggunaan |
| --- | --- |
| 400 | Request malformed/business command invalid |
| 401 | Session tidak valid |
| 403 | Actor terautentikasi tetapi tidak memiliki akses |
| 404 | Resource tidak ada atau disembunyikan karena tenant scope |
| 409 | State/version/idempotency conflict |
| 422 | Field validation |
| 429 | Rate limit |
| 503 | Dependency unavailable dan tidak ada fallback |

## 4. Endpoint inventory

### Identity

| Method | Path | Permission/notes |
| --- | --- | --- |
| POST | `/auth/register` | Public + abuse controls |
| POST | `/auth/login` | Public + rate limit |
| POST | `/auth/refresh` | Refresh cookie rotation |
| POST | `/auth/logout` | Revoke current session |
| POST | `/auth/logout-all` | Revoke all user sessions |
| GET | `/auth/me` | Current user and capabilities |
| POST | `/auth/mfa/challenge` | Step-up auth |
| POST | `/auth/recovery/*` | Enumeration-safe |

### Partner onboarding

| Method | Path | Permission/notes |
| --- | --- | --- |
| POST | `/partners` | Create application |
| GET | `/partners/{partner_id}` | Scoped member/admin |
| PATCH | `/partners/{partner_id}` | Owner/admin |
| POST | `/partners/{partner_id}/documents` | Signed upload flow |
| POST | `/admin/partners/{partner_id}/verify` | Platform verifier |
| POST | `/admin/partners/{partner_id}/block` | Platform admin + reason |

### Catalog and services

| Method | Path | Permission/notes |
| --- | --- | --- |
| GET | `/products` | Public filters/search |
| GET | `/products/{product_id}` | Published only/public |
| POST | `/partners/{partner_id}/products` | Catalog write |
| PATCH | `/partners/{partner_id}/products/{product_id}` | Tenant + ownership |
| POST | `/partners/{partner_id}/products/{product_id}/publish` | Verification checks |
| GET | `/services` | Public filters/service area |
| POST | `/partners/{partner_id}/services` | Service write |
| POST | `/partners/{partner_id}/professionals` | Partner owner/admin |
| PUT | `/professionals/{professional_id}/availability` | Self or partner manager |

### Cart, checkout, order

| Method | Path | Permission/notes |
| --- | --- | --- |
| GET | `/cart` | Customer |
| POST | `/cart/items` | Server revalidates catalog |
| PATCH | `/cart/items/{item_id}` | Customer/cart owner |
| DELETE | `/cart/items/{item_id}` | Customer/cart owner |
| POST | `/checkout/quote` | Creates expiring price snapshot |
| POST | `/checkout/confirm` | Idempotent; stock reservation |
| GET | `/orders` | Customer or partner-scoped view |
| GET | `/orders/{order_id}` | Ownership/tenant policy |
| POST | `/orders/{order_id}/cancel` | State machine |

### Booking and tracking

| Method | Path | Permission/notes |
| --- | --- | --- |
| GET | `/services/{service_id}/slots` | Area + date query |
| POST | `/bookings` | Idempotent; slot lock |
| GET | `/bookings/{booking_id}` | Customer/partner/professional scope |
| POST | `/bookings/{booking_id}/accept` | Assigned professional/partner |
| POST | `/bookings/{booking_id}/start-trip` | Professional |
| POST | `/bookings/{booking_id}/arrive` | Professional/geofence policy |
| POST | `/bookings/{booking_id}/check-in` | OTP + customer presence |
| POST | `/bookings/{booking_id}/complete` | OTP/checklist/evidence policy |
| POST | `/bookings/{booking_id}/cancel` | Cancellation policy |
| GET | `/bookings/{booking_id}/tracking` | Short-lived authorized stream/token |

### Payment, ledger, payout

| Method | Path | Permission/notes |
| --- | --- | --- |
| POST | `/payments/intents` | Idempotent |
| POST | `/webhooks/payments/{provider}` | Signature + replay protection |
| POST | `/payments/{payment_id}/refunds` | Policy + step-up |
| GET | `/partners/{partner_id}/ledger` | Finance role |
| GET | `/partners/{partner_id}/balance` | Finance role |
| POST | `/partners/{partner_id}/payouts` | Owner/finance + MFA |
| POST | `/admin/payouts/{payout_id}/approve` | Separation of duty |

### AI

| Method | Path | Permission/notes |
| --- | --- | --- |
| POST | `/ai/customer/sessions` | Consent + purpose |
| POST | `/ai/customer/recommendations` | Text/photo token; no diagnosis |
| DELETE | `/ai/customer/sessions/{session_id}` | Retention/deletion policy |
| GET | `/partners/{partner_id}/analytics/summary` | Deterministic metrics |
| POST | `/partners/{partner_id}/ai/insights` | Copilot narrative |
| POST | `/ai/feedback` | Quality/safety feedback |

## 5. Idempotency

Untuk mutasi kritis:

1. client mengirim UUID random pada `Idempotency-Key`;
2. server menyimpan key + actor + route + request hash;
3. key yang sama dan payload sama mengembalikan respons pertama;
4. key sama dengan payload berbeda menghasilkan `409`;
5. record memiliki TTL sesuai risiko bisnis;
6. webhook provider dideduplikasi menggunakan provider event ID.

## 6. Concurrency

- Product/service edit menggunakan `version` atau `updated_at` ETag.
- Inventory menggunakan atomic update/row lock, bukan read-modify-write dari UI.
- Slot booking menggunakan database constraint/advisory lock yang scoped dan singkat.
- Payout dan refund menggunakan unique business key.
- State transition dilakukan dengan conditional update:

```sql
UPDATE bookings
SET state = 'confirmed', version = version + 1
WHERE id = :id
  AND state = 'pending_acceptance'
  AND version = :expected_version;
```

Zero affected row berarti conflict, bukan silent success.

## 7. API evolution

- Tambahan optional field bersifat backward-compatible.
- Jangan mengubah arti field existing.
- Enum baru dapat merusak client; generated client harus memiliki unknown fallback.
- Breaking change membutuhkan `/api/v2` atau migration window.
- OpenAPI diff menjadi CI gate.

Outline machine-readable tersedia di `openapi/yoru-api-outline.yaml`. Outline bukan kontrak
final seluruh endpoint; setiap sprint harus memperluas schema dan examples sebelum coding.
