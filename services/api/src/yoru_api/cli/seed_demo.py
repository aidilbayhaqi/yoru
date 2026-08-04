from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import UTC, datetime, time
from typing import TypeVar

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.cli.demo_seed_data import (
    CATEGORIES,
    PARTNERS,
    PRODUCTS,
    PROFESSIONALS,
    SERVICES,
)
from yoru_api.core.database import create_database_engine, create_session_factory
from yoru_api.core.settings import get_settings
from yoru_api.modules.catalog.models import (
    CatalogCategory,
    InventoryItem,
    Product,
    ProductMedia,
    ServiceAvailability,
    ServiceOffering,
    ServiceProfessional,
    ServiceProfessionalAssignment,
)
from yoru_api.modules.identity.models import Partner
from yoru_api.modules.partners.models import ServiceArea

NAMESPACE = uuid.UUID("5ed89430-bde8-4c1d-8de8-9eaa730ff529")
ModelT = TypeVar("ModelT")


def stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


async def by_id(
    session: AsyncSession,
    model: type[ModelT],
    identifier: uuid.UUID,
) -> ModelT | None:
    return await session.get(model, identifier)


async def seed_demo(session: AsyncSession) -> dict[str, int]:
    now = datetime.now(UTC)
    await session.execute(text("SELECT pg_advisory_xact_lock(981_944_217)"))

    categories: dict[str, CatalogCategory] = {}
    for item in CATEGORIES:
        row = await session.scalar(
            select(CatalogCategory).where(CatalogCategory.code == item.code)
        )
        if row is None:
            row = CatalogCategory(
                id=stable_id("category", item.code),
                code=item.code,
                name=item.name,
                description=item.description,
                is_active=True,
            )
            session.add(row)
        else:
            row.name = item.name
            row.description = item.description
            row.is_active = True
        categories[item.code] = row
    await session.flush()

    partners: dict[str, Partner] = {}
    for item in PARTNERS:
        identifier = stable_id("partner", item.key)
        row = await by_id(session, Partner, identifier)
        if row is None:
            row = await session.scalar(
                select(Partner).where(Partner.display_name == item.display_name)
            )
        values = {
            "display_name": item.display_name,
            "legal_name": item.legal_name,
            "partner_type": item.partner_type,
            "contact_email": item.contact_email,
            "contact_phone": item.contact_phone,
            "address_line": item.address_line,
            "city": item.city,
            "province": item.province,
            "postal_code": item.postal_code,
            "description": item.description,
            "status": "verified",
            "submitted_at": now,
            "reviewed_at": now,
            "review_reason": None,
        }
        if row is None:
            row = Partner(id=identifier, **values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        partners[item.key] = row
    await session.flush()

    for item in PARTNERS:
        identifier = stable_id("service-area", item.key)
        row = await by_id(session, ServiceArea, identifier)
        partner = partners[item.key]
        area_name = f"Area layanan {partner.city}"
        if row is None:
            row = await session.scalar(
                select(ServiceArea).where(
                    ServiceArea.partner_id == partner.id,
                    ServiceArea.name == area_name,
                )
            )
        values = {
            "partner_id": partner.id,
            "name": area_name,
            "area_type": "radius",
            "center_latitude": -6.2,
            "center_longitude": 106.82,
            "radius_km": 35.0,
            "postal_codes": [],
            "status": "active",
        }
        if row is None:
            session.add(ServiceArea(id=identifier, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)

    products: dict[str, Product] = {}
    for item in PRODUCTS:
        identifier = stable_id("product", item.key)
        row = await by_id(session, Product, identifier)
        partner = partners[item.partner_key]
        if row is None:
            row = await session.scalar(
                select(Product).where(
                    Product.partner_id == partner.id,
                    Product.slug == item.slug,
                )
            )
        values = {
            "partner_id": partner.id,
            "category_id": categories[item.category_code].id,
            "sku": item.sku,
            "name": item.name,
            "slug": item.slug,
            "description": item.description,
            "unit_price": item.unit_price,
            "currency": "IDR",
            "stock_tracked": True,
            "status": "published",
            "review_reason": None,
            "submitted_at": now,
            "published_at": now,
            "reviewed_at": now,
        }
        if row is None:
            row = Product(id=identifier, **values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        products[item.key] = row
    await session.flush()

    for item in PRODUCTS:
        product = products[item.key]
        inventory_id = stable_id("inventory", item.key)
        inventory = await by_id(session, InventoryItem, inventory_id)
        if inventory is None:
            inventory = await session.scalar(
                select(InventoryItem).where(InventoryItem.product_id == product.id)
            )
        values = {
            "partner_id": product.partner_id,
            "product_id": product.id,
            "on_hand": item.stock,
            "reserved": 0,
            "reorder_level": item.reorder_level,
            "version": 1,
        }
        if inventory is None:
            session.add(InventoryItem(id=inventory_id, **values))
        else:
            for key, value in values.items():
                setattr(inventory, key, value)

        media_id = stable_id("product-media", item.key)
        media = await by_id(session, ProductMedia, media_id)
        if media is None:
            media = await session.scalar(
                select(ProductMedia).where(ProductMedia.object_key == item.image_path)
            )
        media_values = {
            "partner_id": product.partner_id,
            "product_id": product.id,
            "object_key": item.image_path,
            "content_type": "image/png",
            "alt_text": item.alt_text,
            "sort_order": 0,
            "status": "ready",
        }
        if media is None:
            session.add(ProductMedia(id=media_id, **media_values))
        else:
            for key, value in media_values.items():
                setattr(media, key, value)

    professionals: dict[str, ServiceProfessional] = {}
    for item in PROFESSIONALS:
        identifier = stable_id("professional", item.key)
        row = await by_id(session, ServiceProfessional, identifier)
        partner = partners[item.partner_key]
        if row is None:
            row = await session.scalar(
                select(ServiceProfessional).where(
                    ServiceProfessional.partner_id == partner.id,
                    ServiceProfessional.name == item.name,
                )
            )
        values = {
            "partner_id": partner.id,
            "name": item.name,
            "title": item.title,
            "bio": item.bio,
            "is_active": True,
        }
        if row is None:
            row = ServiceProfessional(id=identifier, **values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        professionals[item.key] = row
    await session.flush()

    services: dict[str, ServiceOffering] = {}
    for item in SERVICES:
        identifier = stable_id("service", item.key)
        row = await by_id(session, ServiceOffering, identifier)
        partner = partners[item.partner_key]
        if row is None:
            row = await session.scalar(
                select(ServiceOffering).where(
                    ServiceOffering.partner_id == partner.id,
                    ServiceOffering.slug == item.slug,
                )
            )
        values = {
            "partner_id": partner.id,
            "category_id": categories[item.category_code].id,
            "name": item.name,
            "slug": item.slug,
            "description": item.description,
            "duration_minutes": item.duration_minutes,
            "price": item.price,
            "currency": "IDR",
            "capacity_per_slot": item.capacity_per_slot,
            "booking_notice_minutes": 120,
            "cancellation_window_minutes": 360,
            "status": "published",
            "review_reason": None,
            "submitted_at": now,
            "published_at": now,
            "reviewed_at": now,
        }
        if row is None:
            row = ServiceOffering(id=identifier, **values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        services[item.key] = row
    await session.flush()

    for item in SERVICES:
        service = services[item.key]
        for professional_key in item.professional_keys:
            professional = professionals[professional_key]
            assignment_id = stable_id(
                "service-assignment", f"{item.key}:{professional_key}"
            )
            assignment = await by_id(
                session, ServiceProfessionalAssignment, assignment_id
            )
            if assignment is None:
                assignment = await session.scalar(
                    select(ServiceProfessionalAssignment).where(
                        ServiceProfessionalAssignment.service_id == service.id,
                        ServiceProfessionalAssignment.professional_id == professional.id,
                    )
                )
            values = {
                "partner_id": service.partner_id,
                "service_id": service.id,
                "professional_id": professional.id,
            }
            if assignment is None:
                session.add(
                    ServiceProfessionalAssignment(id=assignment_id, **values)
                )
            else:
                for key, value in values.items():
                    setattr(assignment, key, value)

            for weekday in range(0, 6):
                availability_id = stable_id(
                    "availability",
                    f"{item.key}:{professional_key}:{weekday}",
                )
                availability = await by_id(
                    session, ServiceAvailability, availability_id
                )
                availability_values = {
                    "partner_id": service.partner_id,
                    "service_id": service.id,
                    "professional_id": professional.id,
                    "weekday": weekday,
                    "start_time": time(9, 0),
                    "end_time": time(18, 0),
                    "timezone": "Asia/Jakarta",
                    "slot_interval_minutes": 30,
                    "capacity_override": 1,
                    "is_active": True,
                }
                if availability is None:
                    session.add(
                        ServiceAvailability(
                            id=availability_id,
                            **availability_values,
                        )
                    )
                else:
                    for key, value in availability_values.items():
                        setattr(availability, key, value)

    await session.commit()
    return {
        "categories": len(CATEGORIES),
        "partners": len(PARTNERS),
        "products": len(PRODUCTS),
        "product_media": len(PRODUCTS),
        "professionals": len(PROFESSIONALS),
        "services": len(SERVICES),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed idempotent Yoru demo catalog and home-service data."
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print counts without connecting to PostgreSQL.",
    )
    return parser.parse_args()


async def run_seed() -> dict[str, int]:
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            return await seed_demo(session)
    finally:
        await engine.dispose()


def main() -> None:
    args = parse_args()
    if args.print_only:
        print(
            {
                "categories": len(CATEGORIES),
                "partners": len(PARTNERS),
                "products": len(PRODUCTS),
                "product_media": len(PRODUCTS),
                "professionals": len(PROFESSIONALS),
                "services": len(SERVICES),
            }
        )
        return
    result = asyncio.run(run_seed())
    print(f"Yoru demo seed complete: {result}")


if __name__ == "__main__":
    main()
