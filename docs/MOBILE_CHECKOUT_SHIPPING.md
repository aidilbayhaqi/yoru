# P0 Checkout Shipping Contract

Patch ini menambahkan kontrak shipping yang bisa langsung dipakai Flutter tanpa merusak flow web lama.

## Endpoint

### GET `/api/v1/shipping/options`

Mengembalikan opsi shipping sementara dari adapter `internal_flat_rate`.

### POST `/api/v1/checkout/quote`

Pickup lama tetap valid:

```json
{}
```

Shipping:

```json
{
  "fulfillment_type": "shipping",
  "shipping_service": "regular",
  "shipping_address": {
    "recipient_name": "Ucok",
    "recipient_phone": "+628123456789",
    "address_line1": "Jl. Contoh No. 1",
    "address_line2": null,
    "district": "Kebayoran Baru",
    "city": "Jakarta Selatan",
    "province": "DKI Jakarta",
    "postal_code": "12110",
    "country_code": "ID",
    "delivery_note": "Pagar hitam",
    "latitude": -6.24,
    "longitude": 106.8
  }
}
```

Quote menyimpan:

- `shipping_address_snapshot`
- `shipping_method_snapshot`
- ongkir di `shipping_amount`
- total baru di `total_amount`

Saat checkout dikonfirmasi, snapshot tersebut disalin ke order. Perubahan alamat user setelah transaksi tidak mengubah histori order.

## Batasan adapter saat ini

`internal_flat_rate` adalah adapter sementara dan deterministic untuk development:

- regular: Rp20.000
- express: Rp35.000
- same day: Rp55.000

Strukturnya sengaja dipisahkan di `commerce/shipping.py` supaya batch berikutnya bisa mengganti perhitungan dengan RajaOngkir, Biteship, Shipper, atau provider lain tanpa mengubah kontrak Flutter.
