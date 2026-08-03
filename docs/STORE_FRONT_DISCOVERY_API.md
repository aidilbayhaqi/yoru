# Storefront Discovery API Contract

This document defines the backend seam expected by Storefront Experience v5.
The frontend patch does not pretend that browser-side inference is authoritative.

## 1. Unified query search

`GET /api/v1/discovery/search`

Query parameters:

- `q`
- `kind=all|product|service`
- `category`
- `partner_id`
- `service_area`
- `price_max_minor`
- `rating_min`
- `in_stock`
- `sort`
- `cursor`
- `limit`

Response:

```json
{
  "items": [],
  "next_cursor": null,
  "facets": {
    "categories": [],
    "partners": [],
    "service_areas": [],
    "price_ranges": []
  },
  "request_id": "..."
}
```

Rules:

- tenant and publication filters are server-side
- unpublished catalog items are never returned
- price and stock are read from transactional sources
- cursor is opaque
- unsupported filters return structured validation errors

## 2. AI intent parsing

`POST /api/v1/advisor/search-intent`

```json
{
  "message": "skincare simpel untuk barrier di bawah 350 ribu",
  "locale": "id-ID",
  "consent": {
    "personalization": false
  }
}
```

Response:

```json
{
  "intent": {
    "query": "skin barrier",
    "kind": "product",
    "categories": ["Skincare"],
    "price_max_minor": 35000000,
    "service_area": null,
    "constraints": []
  },
  "explanation": "Mencari produk skincare untuk mendukung skin barrier.",
  "policy_version": "advisor-search-v1",
  "request_id": "..."
}
```

The intent endpoint may propose filters. It must not provide final price, stock,
medical diagnosis, payment state, booking availability, or professional assignment.

## 3. Visual search

### Create upload

`POST /api/v1/media/uploads`

```json
{
  "purpose": "visual_search",
  "content_type": "image/jpeg",
  "size_bytes": 482101
}
```

Response contains a short-lived signed upload target and an opaque media ID.

### Start visual search

`POST /api/v1/advisor/visual-search`

```json
{
  "media_id": "med_...",
  "kind": "product",
  "category_hint": "fashion",
  "limit": 24
}
```

Response:

```json
{
  "items": [
    {
      "catalog_item_id": "prd_...",
      "score": 0.84,
      "reason": "similar silhouette and category"
    }
  ],
  "model_version": "clip-...",
  "index_version": "catalog-...",
  "request_id": "..."
}
```

Required controls:

- MIME and file-signature validation
- maximum file size
- malware scan where applicable
- image moderation
- EXIF removal
- short retention for raw uploads
- tenant and publication filters after vector retrieval
- confidence threshold
- no face identity matching
- no sensitive-attribute inference
- request, model, policy, and index version logging

## 4. Collections and deals

- `GET /api/v1/catalog/collections`
- `GET /api/v1/catalog/collections/{slug}`
- `GET /api/v1/catalog/deals`

A collection is editorial ordering. A deal is a pricing/promotion decision.
They should not share the same source of truth.

## 5. Serviceability

`POST /api/v1/bookings/serviceability`

```json
{
  "service_id": "svc_...",
  "address": {
    "latitude": -6.2,
    "longitude": 106.8,
    "postal_code": "12345"
  }
}
```

The response should state serviceability, reason, available transport fee rules,
and the serviceability version used. Advertised area text is not sufficient to
lock a booking.
