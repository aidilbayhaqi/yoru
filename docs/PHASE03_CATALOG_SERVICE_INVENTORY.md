# Phase 3 — Catalog, Service, and Inventory

## Release

- Version: `0.4.0`
- Requires: `0.3.0`
- Migration: `20260801_0004`

## Domain coverage

### Product catalog

Products are partner-owned and categorized by globally seeded categories. Product records contain
partner SKU, slug, description, price, currency, stock-tracking mode, review state, and moderation
metadata. Media registration accepts object-storage metadata only and emits audit records.

### Inventory

Every stock-tracked product can have one inventory row. The row stores `on_hand`, `reserved`,
`reorder_level`, and an optimistic `version`. Partner stock updates can include `expected_version`
to reject stale writes. Database constraints prevent negative quantities and prevent reserved stock
from exceeding physical stock.

### Services and professionals

Service offerings contain duration, capacity, notice windows, cancellation windows, and price.
Partners can add professionals, assign them to services, and define weekly availability rules.
Submitting a service for review requires at least one availability rule.

### Moderation

Products and services use this state model:

```text
draft -> pending_review -> published
                        -> revision_required -> pending_review
                        -> rejected -> draft
published -> archived -> draft
```

Publishing, revision requests, and rejection require `platform.catalog.review`; moderation commands
also require recent MFA. Editing a published record returns it to draft for re-review.

## Permissions

Partner roles `partner_owner` and `partner_admin` receive:

- `catalog.product.read`
- `catalog.product.write`
- `catalog.product.submit`
- `catalog.service.read`
- `catalog.service.write`
- `catalog.service.submit`
- `catalog.inventory.write`
- `catalog.availability.write`
- `catalog.professional.write`

`platform_verifier` receives `platform.catalog.review`. `super_admin` receives all permissions.

## RLS behavior

Published products and services are publicly selectable. Partner members and platform admins can
select tenant drafts and perform writes. Dependent inventory, media, professionals, assignments,
and availability rows are publicly selectable only when linked to published parent records.

## Main endpoints

### Public

- `GET /api/v1/catalog/categories`
- `GET /api/v1/catalog/products`
- `GET /api/v1/catalog/products/{product_id}`
- `GET /api/v1/catalog/services`
- `GET /api/v1/catalog/services/{service_id}`

### Partner

- `GET|POST /api/v1/partner/catalog/products`
- `PATCH /api/v1/partner/catalog/products/{product_id}`
- `POST /api/v1/partner/catalog/products/{product_id}/media`
- `POST /api/v1/partner/catalog/products/{product_id}/submit`
- `POST /api/v1/partner/catalog/products/{product_id}/archive`
- `PUT /api/v1/partner/catalog/products/{product_id}/inventory`
- `GET|POST /api/v1/partner/catalog/services`
- `PATCH /api/v1/partner/catalog/services/{service_id}`
- `POST /api/v1/partner/catalog/services/{service_id}/availability`
- `POST /api/v1/partner/catalog/services/{service_id}/submit`
- `POST /api/v1/partner/catalog/services/{service_id}/archive`
- `GET|POST /api/v1/partner/catalog/professionals`
- `POST /api/v1/partner/catalog/services/{service_id}/professionals/{professional_id}`

### Platform review

- `GET /api/v1/admin/catalog/products?status=pending_review`
- `POST /api/v1/admin/catalog/products/{product_id}/moderate`
- `GET /api/v1/admin/catalog/services?status=pending_review`
- `POST /api/v1/admin/catalog/services/{service_id}/moderate`

## Next phase

Phase 4 should build carts, inventory reservations with expiry, checkout idempotency, orders,
bookings, pricing snapshots, and cancellation transitions on top of these entities.
