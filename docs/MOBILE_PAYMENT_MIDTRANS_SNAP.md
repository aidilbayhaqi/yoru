# P0 Mobile Payment Contract — Midtrans Snap

Patch ini mengganti payment mock-only menjadi provider abstraction dengan Midtrans Snap.

## Provider

- `mock`: local development.
- `midtrans_snap`: hosted checkout Midtrans untuk staging/production.

## Environment

```env
PAYMENT_ENABLED_PROVIDERS=mock

# Staging / sandbox
# PAYMENT_ENABLED_PROVIDERS=midtrans_snap
MIDTRANS_SERVER_KEY=
MIDTRANS_CLIENT_KEY=
MIDTRANS_IS_PRODUCTION=false
MIDTRANS_SNAP_BASE_URL=
MIDTRANS_ENABLED_PAYMENTS=qris,gopay,bank_transfer
MIDTRANS_FINISH_REDIRECT_URL=
MIDTRANS_ERROR_REDIRECT_URL=
```

`MIDTRANS_SERVER_KEY` hanya boleh berada di backend. Jangan kirim ke Flutter.

## Membuat payment saat checkout

```http
POST /api/v1/checkout/confirm
Authorization: Bearer <access-token>
Idempotency-Key: <unique-key>
Content-Type: application/json

{
  "quote_id": "...",
  "payment_provider": "midtrans_snap"
}
```

Response:

```json
{
  "provider": "midtrans_snap",
  "provider_reference": "YORU-20260805-ABCD1234",
  "provider_status": "PENDING",
  "status": "requires_action",
  "client_token": "<snap-token>",
  "actions": [
    {
      "type": "REDIRECT_CUSTOMER",
      "descriptor": "WEB_URL",
      "value": "https://app.sandbox.midtrans.com/snap/v4/redirection/..."
    }
  ]
}
```

Flutter membuka action `WEB_URL` memakai external browser atau in-app browser. Status final tetap dibaca dari backend, bukan dari query redirect.

## Polling status lokal

```http
GET /api/v1/payments/intents/{payment_intent_id}
Authorization: Bearer <access-token>
```

## Webhook

```text
POST /api/v1/webhooks/payments/midtrans_snap
```

Atur URL itu sebagai Payment Notification URL di Midtrans Dashboard.

Backend memverifikasi:

```text
SHA512(order_id + status_code + gross_amount + MIDTRANS_SERVER_KEY)
```

Backend juga membandingkan `gross_amount` dan `currency` webhook dengan payment intent lokal, menyimpan event secara idempotent, dan tidak melepas stok saat status masih `pending`.

## Status mapping

```text
settlement                    -> succeeded
capture + fraud accept        -> succeeded
capture + fraud challenge     -> pending
pending                       -> pending
deny                          -> failed
cancel                        -> cancelled
expire                        -> expired
```
