import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
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


@dataclass(frozen=True, slots=True)
class ProductBundle:
    product: Product
    inventory: InventoryItem | None
    media: list[ProductMedia]


@dataclass(frozen=True, slots=True)
class ServiceBundle:
    service: ServiceOffering
    availability: list[ServiceAvailability]
    professionals: list[ServiceProfessional]


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_categories(self) -> list[CatalogCategory]:
        result = await self._session.scalars(
            select(CatalogCategory)
            .where(CatalogCategory.is_active.is_(True))
            .order_by(CatalogCategory.name.asc())
        )
        return list(result)

    async def get_category(self, category_id: uuid.UUID) -> CatalogCategory | None:
        return await self._session.scalar(
            select(CatalogCategory).where(
                CatalogCategory.id == category_id,
                CatalogCategory.is_active.is_(True),
            )
        )

    async def get_product(
        self,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product | None:
        statement: Select[tuple[Product]] = select(Product).where(Product.id == product_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_product_by_slug(
        self,
        *,
        partner_id: uuid.UUID,
        slug: str,
        exclude_id: uuid.UUID | None = None,
    ) -> Product | None:
        statement = select(Product).where(
            Product.partner_id == partner_id,
            Product.slug == slug,
        )
        if exclude_id is not None:
            statement = statement.where(Product.id != exclude_id)
        return await self._session.scalar(statement)

    async def list_products(
        self,
        *,
        partner_id: uuid.UUID | None,
        published_only: bool,
        category_id: uuid.UUID | None,
        status: str | None = None,
        limit: int,
    ) -> list[Product]:
        statement = select(Product)
        if partner_id is not None:
            statement = statement.where(Product.partner_id == partner_id)
        if published_only:
            statement = statement.where(Product.status == "published")
        elif status is not None:
            statement = statement.where(Product.status == status)
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        result = await self._session.scalars(
            statement.order_by(Product.updated_at.desc(), Product.id.desc()).limit(limit)
        )
        return list(result)

    async def add_product(
        self,
        *,
        partner_id: uuid.UUID,
        values: dict[str, object],
    ) -> Product:
        product = Product(partner_id=partner_id, **values)
        self._session.add(product)
        await self._session.flush()
        return product

    async def get_inventory(
        self,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> InventoryItem | None:
        statement: Select[tuple[InventoryItem]] = select(InventoryItem).where(
            InventoryItem.product_id == product_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_inventory(
        self,
        *,
        partner_id: uuid.UUID,
        product_id: uuid.UUID,
        on_hand: int,
        reorder_level: int,
    ) -> InventoryItem:
        inventory = InventoryItem(
            partner_id=partner_id,
            product_id=product_id,
            on_hand=on_hand,
            reserved=0,
            reorder_level=reorder_level,
            version=1,
        )
        self._session.add(inventory)
        await self._session.flush()
        return inventory

    async def list_product_media(self, product_id: uuid.UUID) -> list[ProductMedia]:
        result = await self._session.scalars(
            select(ProductMedia)
            .where(ProductMedia.product_id == product_id)
            .order_by(ProductMedia.sort_order.asc(), ProductMedia.id.asc())
        )
        return list(result)

    async def add_product_media(
        self,
        *,
        partner_id: uuid.UUID,
        product_id: uuid.UUID,
        values: dict[str, object],
    ) -> ProductMedia:
        media = ProductMedia(
            partner_id=partner_id,
            product_id=product_id,
            **values,
        )
        self._session.add(media)
        await self._session.flush()
        return media

    async def product_bundle(self, product: Product) -> ProductBundle:
        inventory = await self.get_inventory(product.id)
        media = await self.list_product_media(product.id)
        return ProductBundle(product=product, inventory=inventory, media=media)

    async def product_bundles(self, products: list[Product]) -> list[ProductBundle]:
        return [await self.product_bundle(product) for product in products]

    async def get_service(
        self,
        service_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> ServiceOffering | None:
        statement: Select[tuple[ServiceOffering]] = select(ServiceOffering).where(
            ServiceOffering.id == service_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def get_service_by_slug(
        self,
        *,
        partner_id: uuid.UUID,
        slug: str,
        exclude_id: uuid.UUID | None = None,
    ) -> ServiceOffering | None:
        statement = select(ServiceOffering).where(
            ServiceOffering.partner_id == partner_id,
            ServiceOffering.slug == slug,
        )
        if exclude_id is not None:
            statement = statement.where(ServiceOffering.id != exclude_id)
        return await self._session.scalar(statement)

    async def list_services(
        self,
        *,
        partner_id: uuid.UUID | None,
        published_only: bool,
        category_id: uuid.UUID | None,
        status: str | None = None,
        limit: int,
    ) -> list[ServiceOffering]:
        statement = select(ServiceOffering)
        if partner_id is not None:
            statement = statement.where(ServiceOffering.partner_id == partner_id)
        if published_only:
            statement = statement.where(ServiceOffering.status == "published")
        elif status is not None:
            statement = statement.where(ServiceOffering.status == status)
        if category_id is not None:
            statement = statement.where(ServiceOffering.category_id == category_id)
        result = await self._session.scalars(
            statement.order_by(
                ServiceOffering.updated_at.desc(), ServiceOffering.id.desc()
            ).limit(limit)
        )
        return list(result)

    async def add_service(
        self,
        *,
        partner_id: uuid.UUID,
        values: dict[str, object],
    ) -> ServiceOffering:
        service = ServiceOffering(partner_id=partner_id, **values)
        self._session.add(service)
        await self._session.flush()
        return service

    async def add_availability(
        self,
        *,
        partner_id: uuid.UUID,
        service_id: uuid.UUID,
        values: dict[str, object],
    ) -> ServiceAvailability:
        item = ServiceAvailability(
            partner_id=partner_id,
            service_id=service_id,
            **values,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_availability(self, service_id: uuid.UUID) -> list[ServiceAvailability]:
        result = await self._session.scalars(
            select(ServiceAvailability)
            .where(ServiceAvailability.service_id == service_id)
            .order_by(
                ServiceAvailability.weekday.asc(),
                ServiceAvailability.start_time.asc(),
                ServiceAvailability.id.asc(),
            )
        )
        return list(result)

    async def get_professional(
        self,
        professional_id: uuid.UUID,
    ) -> ServiceProfessional | None:
        return await self._session.scalar(
            select(ServiceProfessional).where(ServiceProfessional.id == professional_id)
        )

    async def add_professional(
        self,
        *,
        partner_id: uuid.UUID,
        values: dict[str, object],
    ) -> ServiceProfessional:
        professional = ServiceProfessional(partner_id=partner_id, **values)
        self._session.add(professional)
        await self._session.flush()
        return professional

    async def list_professionals(self, partner_id: uuid.UUID) -> list[ServiceProfessional]:
        result = await self._session.scalars(
            select(ServiceProfessional)
            .where(ServiceProfessional.partner_id == partner_id)
            .order_by(ServiceProfessional.name.asc(), ServiceProfessional.id.asc())
        )
        return list(result)

    async def assign_professional(
        self,
        *,
        partner_id: uuid.UUID,
        service_id: uuid.UUID,
        professional_id: uuid.UUID,
    ) -> ServiceProfessionalAssignment:
        assignment = ServiceProfessionalAssignment(
            partner_id=partner_id,
            service_id=service_id,
            professional_id=professional_id,
        )
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def list_service_professionals(
        self,
        service_id: uuid.UUID,
    ) -> list[ServiceProfessional]:
        result = await self._session.scalars(
            select(ServiceProfessional)
            .join(
                ServiceProfessionalAssignment,
                ServiceProfessionalAssignment.professional_id == ServiceProfessional.id,
            )
            .where(ServiceProfessionalAssignment.service_id == service_id)
            .order_by(ServiceProfessional.name.asc(), ServiceProfessional.id.asc())
        )
        return list(result)

    async def service_bundle(self, service: ServiceOffering) -> ServiceBundle:
        availability = await self.list_availability(service.id)
        professionals = await self.list_service_professionals(service.id)
        return ServiceBundle(
            service=service,
            availability=availability,
            professionals=professionals,
        )

    async def service_bundles(
        self,
        services: list[ServiceOffering],
    ) -> list[ServiceBundle]:
        return [await self.service_bundle(service) for service in services]

    def add_audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=partner_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    def add_outbox(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

    async def rollback(self) -> None:
        await self._session.rollback()
