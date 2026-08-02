import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from yoru_api.core.problem import AppError
from yoru_api.modules.catalog.domain import ensure_inventory_balance, slugify
from yoru_api.modules.catalog.models import (
    CatalogCategory,
    InventoryItem,
    Product,
    ProductMedia,
    ServiceAvailability,
    ServiceOffering,
    ServiceProfessional,
)
from yoru_api.modules.catalog.repository import (
    CatalogRepository,
    ProductBundle,
    ServiceBundle,
)
from yoru_api.modules.catalog.schemas import (
    CreateAvailabilityRequest,
    CreateProductRequest,
    CreateProfessionalRequest,
    CreateServiceRequest,
    ModerationRequest,
    RegisterProductMediaRequest,
    UpdateInventoryRequest,
    UpdateProductRequest,
    UpdateServiceRequest,
)
from yoru_api.modules.catalog.state_machine import ensure_catalog_transition
from yoru_api.modules.identity.permissions import Actor, require_permission


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    @staticmethod
    def _active_partner_id(actor: Actor) -> uuid.UUID:
        if actor.active_partner_id is None:
            raise AppError(
                409,
                "ACTIVE_PARTNER_REQUIRED",
                "Select an active partner before managing catalog data",
            )
        return actor.active_partner_id

    async def _required_category(self, category_id: uuid.UUID) -> CatalogCategory:
        category = await self._repository.get_category(category_id)
        if category is None:
            raise AppError(404, "CATALOG_CATEGORY_NOT_FOUND", "Catalog category not found")
        return category

    async def _required_product(
        self,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product:
        product = await self._repository.get_product(product_id, for_update=for_update)
        if product is None:
            raise AppError(404, "CATALOG_PRODUCT_NOT_FOUND", "Catalog product not found")
        return product

    async def _required_service(
        self,
        service_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> ServiceOffering:
        service = await self._repository.get_service(service_id, for_update=for_update)
        if service is None:
            raise AppError(404, "SERVICE_NOT_FOUND", "Service offering not found")
        return service

    @staticmethod
    def _ensure_partner_ownership(resource_partner_id: uuid.UUID, partner_id: uuid.UUID) -> None:
        if resource_partner_id != partner_id:
            raise AppError(404, "CATALOG_RESOURCE_NOT_FOUND", "Catalog resource not found")

    @staticmethod
    def _ensure_editable(status: str) -> None:
        if status not in {"draft", "revision_required", "rejected", "published"}:
            raise AppError(
                409,
                "CATALOG_EDIT_BLOCKED",
                "Catalog item cannot be edited in its current state",
            )

    @staticmethod
    def _moderation_target(decision: str) -> str:
        return {
            "publish": "published",
            "revision_required": "revision_required",
            "reject": "rejected",
        }[decision]

    async def list_categories(self) -> list[CatalogCategory]:
        return await self._repository.list_categories()

    async def list_public_products(
        self,
        *,
        category_id: uuid.UUID | None,
        limit: int,
    ) -> list[ProductBundle]:
        products = await self._repository.list_products(
            partner_id=None,
            published_only=True,
            category_id=category_id,
            status=None,
            limit=limit,
        )
        return await self._repository.product_bundles(products)

    async def get_public_product(self, product_id: uuid.UUID) -> ProductBundle:
        product = await self._required_product(product_id)
        if product.status != "published":
            raise AppError(404, "CATALOG_PRODUCT_NOT_FOUND", "Catalog product not found")
        return await self._repository.product_bundle(product)

    async def list_partner_products(
        self,
        *,
        actor: Actor,
        limit: int,
    ) -> list[ProductBundle]:
        partner_id = self._active_partner_id(actor)
        require_permission(actor, "catalog.product.read", partner_id=partner_id)
        products = await self._repository.list_products(
            partner_id=partner_id,
            published_only=False,
            category_id=None,
            status=None,
            limit=limit,
        )
        return await self._repository.product_bundles(products)

    async def list_review_products(
        self,
        *,
        actor: Actor,
        status: str | None,
        limit: int,
    ) -> list[ProductBundle]:
        require_permission(actor, "platform.catalog.review")
        products = await self._repository.list_products(
            partner_id=None,
            published_only=False,
            category_id=None,
            status=status,
            limit=limit,
        )
        return await self._repository.product_bundles(products)

    async def create_product(
        self,
        *,
        actor: Actor,
        payload: CreateProductRequest,
    ) -> ProductBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        await self._required_category(payload.category_id)
        slug = slugify(payload.slug or payload.name)
        if await self._repository.get_product_by_slug(partner_id=partner_id, slug=slug):
            raise AppError(409, "CATALOG_SLUG_CONFLICT", "Product slug is already in use")
        values = payload.model_dump(
            exclude={"initial_stock", "reorder_level", "slug"}
        )
        values["slug"] = slug
        try:
            product = await self._repository.add_product(
                partner_id=partner_id,
                values=values,
            )
            inventory = None
            if product.stock_tracked:
                inventory = await self._repository.add_inventory(
                    partner_id=partner_id,
                    product_id=product.id,
                    on_hand=payload.initial_stock,
                    reorder_level=payload.reorder_level,
                )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.product.created",
                resource_type="catalog_product",
                resource_id=str(product.id),
                metadata={"status": product.status},
            )
            self._repository.add_outbox(
                aggregate_type="catalog_product",
                aggregate_id=str(product.id),
                event_type="catalog.product.created",
                payload={"partner_id": str(partner_id), "product_id": str(product.id)},
            )
            await self._repository.commit()
            return ProductBundle(product=product, inventory=inventory, media=[])
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "CATALOG_PRODUCT_CONFLICT",
                "Product SKU or slug is already in use",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise

    async def update_product(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
        payload: UpdateProductRequest,
    ) -> ProductBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            product = await self._required_product(product_id, for_update=True)
            self._ensure_partner_ownership(product.partner_id, partner_id)
            self._ensure_editable(product.status)
            values = {
                key: value
                for key, value in payload.model_dump(exclude_unset=True).items()
                if value is not None
            }
            if "category_id" in values:
                await self._required_category(values["category_id"])
            if "slug" in values or "name" in values:
                slug = slugify(str(values.get("slug") or values.get("name") or product.name))
                conflict = await self._repository.get_product_by_slug(
                    partner_id=partner_id,
                    slug=slug,
                    exclude_id=product.id,
                )
                if conflict is not None:
                    raise AppError(
                        409,
                        "CATALOG_SLUG_CONFLICT",
                        "Product slug is already in use",
                    )
                values["slug"] = slug
            for key, value in values.items():
                setattr(product, key, value)
            inventory = await self._repository.get_inventory(product.id, for_update=True)
            if product.stock_tracked and inventory is None:
                await self._repository.add_inventory(
                    partner_id=partner_id,
                    product_id=product.id,
                    on_hand=0,
                    reorder_level=0,
                )
            if product.status == "published":
                product.status = "draft"
                product.review_reason = "Edited after publication; resubmission required."
                product.published_at = None
            elif product.status in {"revision_required", "rejected"}:
                product.status = "draft"
                product.review_reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.product.updated",
                resource_type="catalog_product",
                resource_id=str(product.id),
                metadata={"status": product.status},
            )
            await self._repository.commit()
            return await self._repository.product_bundle(product)
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "CATALOG_PRODUCT_CONFLICT",
                "Product SKU or slug is already in use",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise

    async def register_product_media(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
        payload: RegisterProductMediaRequest,
    ) -> ProductMedia:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            product = await self._required_product(product_id, for_update=True)
            self._ensure_partner_ownership(product.partner_id, partner_id)
            self._ensure_editable(product.status)
            media = await self._repository.add_product_media(
                partner_id=partner_id,
                product_id=product.id,
                values=payload.model_dump(),
            )
            if product.status == "published":
                product.status = "draft"
                product.published_at = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.product.media_registered",
                resource_type="catalog_product_media",
                resource_id=str(media.id),
                metadata={"product_id": str(product.id)},
            )
            await self._repository.commit()
            return media
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "CATALOG_MEDIA_CONFLICT",
                "Media object key is already registered",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise

    async def submit_product(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
    ) -> ProductBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.product.submit",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            product = await self._required_product(product_id, for_update=True)
            self._ensure_partner_ownership(product.partner_id, partner_id)
            ensure_catalog_transition(product.status, "pending_review")
            if len(product.description.strip()) < 10:
                raise AppError(
                    422,
                    "CATALOG_PRODUCT_INCOMPLETE",
                    "Product description is incomplete",
                )
            product.status = "pending_review"
            product.submitted_at = datetime.now(UTC)
            product.review_reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.product.submitted",
                resource_type="catalog_product",
                resource_id=str(product.id),
            )
            self._repository.add_outbox(
                aggregate_type="catalog_product",
                aggregate_id=str(product.id),
                event_type="catalog.product.submitted",
                payload={"partner_id": str(partner_id), "product_id": str(product.id)},
            )
            await self._repository.commit()
            return await self._repository.product_bundle(product)
        except Exception:
            await self._repository.rollback()
            raise

    async def moderate_product(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
        payload: ModerationRequest,
    ) -> ProductBundle:
        require_permission(actor, "platform.catalog.review", require_mfa=True)
        try:
            product = await self._required_product(product_id, for_update=True)
            target = self._moderation_target(payload.decision)
            ensure_catalog_transition(product.status, target)
            now = datetime.now(UTC)
            product.status = target
            product.reviewed_at = now
            product.reviewed_by_user_id = actor.user_id
            product.review_reason = payload.reason
            product.published_at = now if target == "published" else None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=product.partner_id,
                action=f"catalog.product.{target}",
                resource_type="catalog_product",
                resource_id=str(product.id),
                metadata={"reason": payload.reason or ""},
            )
            self._repository.add_outbox(
                aggregate_type="catalog_product",
                aggregate_id=str(product.id),
                event_type=f"catalog.product.{target}",
                payload={
                    "partner_id": str(product.partner_id),
                    "product_id": str(product.id),
                    "status": target,
                },
            )
            await self._repository.commit()
            return await self._repository.product_bundle(product)
        except Exception:
            await self._repository.rollback()
            raise

    async def archive_product(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
    ) -> ProductBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.product.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            product = await self._required_product(product_id, for_update=True)
            self._ensure_partner_ownership(product.partner_id, partner_id)
            ensure_catalog_transition(product.status, "archived")
            product.status = "archived"
            product.published_at = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.product.archived",
                resource_type="catalog_product",
                resource_id=str(product.id),
            )
            await self._repository.commit()
            return await self._repository.product_bundle(product)
        except Exception:
            await self._repository.rollback()
            raise

    async def update_inventory(
        self,
        *,
        actor: Actor,
        product_id: uuid.UUID,
        payload: UpdateInventoryRequest,
    ) -> InventoryItem:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.inventory.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            product = await self._required_product(product_id, for_update=True)
            self._ensure_partner_ownership(product.partner_id, partner_id)
            if not product.stock_tracked:
                raise AppError(
                    409,
                    "INVENTORY_NOT_TRACKED",
                    "Inventory is disabled for this product",
                )
            inventory = await self._repository.get_inventory(product.id, for_update=True)
            if inventory is None:
                inventory = await self._repository.add_inventory(
                    partner_id=partner_id,
                    product_id=product.id,
                    on_hand=0,
                    reorder_level=0,
                )
            if (
                payload.expected_version is not None
                and inventory.version != payload.expected_version
            ):
                raise AppError(
                    409,
                    "INVENTORY_VERSION_CONFLICT",
                    "Inventory was changed by another request",
                )
            ensure_inventory_balance(on_hand=payload.on_hand, reserved=inventory.reserved)
            inventory.on_hand = payload.on_hand
            inventory.reorder_level = payload.reorder_level
            inventory.version += 1
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="inventory.stock.updated",
                resource_type="inventory_item",
                resource_id=str(inventory.id),
                metadata={
                    "product_id": str(product.id),
                    "on_hand": inventory.on_hand,
                    "reserved": inventory.reserved,
                    "version": inventory.version,
                },
            )
            self._repository.add_outbox(
                aggregate_type="inventory_item",
                aggregate_id=str(inventory.id),
                event_type="inventory.stock.updated",
                payload={
                    "partner_id": str(partner_id),
                    "product_id": str(product.id),
                    "available": inventory.available,
                    "version": inventory.version,
                },
            )
            await self._repository.commit()
            return inventory
        except Exception:
            await self._repository.rollback()
            raise

    async def list_public_services(
        self,
        *,
        category_id: uuid.UUID | None,
        limit: int,
    ) -> list[ServiceBundle]:
        services = await self._repository.list_services(
            partner_id=None,
            published_only=True,
            category_id=category_id,
            status=None,
            limit=limit,
        )
        return await self._repository.service_bundles(services)

    async def get_public_service(self, service_id: uuid.UUID) -> ServiceBundle:
        service = await self._required_service(service_id)
        if service.status != "published":
            raise AppError(404, "SERVICE_NOT_FOUND", "Service offering not found")
        return await self._repository.service_bundle(service)

    async def list_partner_services(
        self,
        *,
        actor: Actor,
        limit: int,
    ) -> list[ServiceBundle]:
        partner_id = self._active_partner_id(actor)
        require_permission(actor, "catalog.service.read", partner_id=partner_id)
        services = await self._repository.list_services(
            partner_id=partner_id,
            published_only=False,
            category_id=None,
            status=None,
            limit=limit,
        )
        return await self._repository.service_bundles(services)

    async def list_review_services(
        self,
        *,
        actor: Actor,
        status: str | None,
        limit: int,
    ) -> list[ServiceBundle]:
        require_permission(actor, "platform.catalog.review")
        services = await self._repository.list_services(
            partner_id=None,
            published_only=False,
            category_id=None,
            status=status,
            limit=limit,
        )
        return await self._repository.service_bundles(services)

    async def create_service(
        self,
        *,
        actor: Actor,
        payload: CreateServiceRequest,
    ) -> ServiceBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.service.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        await self._required_category(payload.category_id)
        slug = slugify(payload.slug or payload.name)
        if await self._repository.get_service_by_slug(partner_id=partner_id, slug=slug):
            raise AppError(409, "CATALOG_SLUG_CONFLICT", "Service slug is already in use")
        values = payload.model_dump(exclude={"slug"})
        values["slug"] = slug
        try:
            service = await self._repository.add_service(
                partner_id=partner_id,
                values=values,
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.service.created",
                resource_type="service_offering",
                resource_id=str(service.id),
                metadata={"status": service.status},
            )
            self._repository.add_outbox(
                aggregate_type="service_offering",
                aggregate_id=str(service.id),
                event_type="catalog.service.created",
                payload={"partner_id": str(partner_id), "service_id": str(service.id)},
            )
            await self._repository.commit()
            return ServiceBundle(service=service, availability=[], professionals=[])
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "CATALOG_SERVICE_CONFLICT",
                "Service slug is already in use",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise

    async def update_service(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
        payload: UpdateServiceRequest,
    ) -> ServiceBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.service.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            service = await self._required_service(service_id, for_update=True)
            self._ensure_partner_ownership(service.partner_id, partner_id)
            self._ensure_editable(service.status)
            values = {
                key: value
                for key, value in payload.model_dump(exclude_unset=True).items()
                if value is not None
            }
            if "category_id" in values:
                await self._required_category(values["category_id"])
            if "slug" in values or "name" in values:
                slug = slugify(str(values.get("slug") or values.get("name") or service.name))
                conflict = await self._repository.get_service_by_slug(
                    partner_id=partner_id,
                    slug=slug,
                    exclude_id=service.id,
                )
                if conflict is not None:
                    raise AppError(
                        409,
                        "CATALOG_SLUG_CONFLICT",
                        "Service slug is already in use",
                    )
                values["slug"] = slug
            for key, value in values.items():
                setattr(service, key, value)
            if service.status == "published":
                service.status = "draft"
                service.review_reason = "Edited after publication; resubmission required."
                service.published_at = None
            elif service.status in {"revision_required", "rejected"}:
                service.status = "draft"
                service.review_reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.service.updated",
                resource_type="service_offering",
                resource_id=str(service.id),
                metadata={"status": service.status},
            )
            await self._repository.commit()
            return await self._repository.service_bundle(service)
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "CATALOG_SERVICE_CONFLICT",
                "Service slug is already in use",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise

    async def submit_service(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
    ) -> ServiceBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.service.submit",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            service = await self._required_service(service_id, for_update=True)
            self._ensure_partner_ownership(service.partner_id, partner_id)
            ensure_catalog_transition(service.status, "pending_review")
            availability = await self._repository.list_availability(service.id)
            if not availability:
                raise AppError(
                    422,
                    "SERVICE_AVAILABILITY_REQUIRED",
                    "At least one availability rule is required before submission",
                )
            service.status = "pending_review"
            service.submitted_at = datetime.now(UTC)
            service.review_reason = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.service.submitted",
                resource_type="service_offering",
                resource_id=str(service.id),
            )
            self._repository.add_outbox(
                aggregate_type="service_offering",
                aggregate_id=str(service.id),
                event_type="catalog.service.submitted",
                payload={"partner_id": str(partner_id), "service_id": str(service.id)},
            )
            await self._repository.commit()
            return await self._repository.service_bundle(service)
        except Exception:
            await self._repository.rollback()
            raise

    async def moderate_service(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
        payload: ModerationRequest,
    ) -> ServiceBundle:
        require_permission(actor, "platform.catalog.review", require_mfa=True)
        try:
            service = await self._required_service(service_id, for_update=True)
            target = self._moderation_target(payload.decision)
            ensure_catalog_transition(service.status, target)
            now = datetime.now(UTC)
            service.status = target
            service.reviewed_at = now
            service.reviewed_by_user_id = actor.user_id
            service.review_reason = payload.reason
            service.published_at = now if target == "published" else None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=service.partner_id,
                action=f"catalog.service.{target}",
                resource_type="service_offering",
                resource_id=str(service.id),
                metadata={"reason": payload.reason or ""},
            )
            self._repository.add_outbox(
                aggregate_type="service_offering",
                aggregate_id=str(service.id),
                event_type=f"catalog.service.{target}",
                payload={
                    "partner_id": str(service.partner_id),
                    "service_id": str(service.id),
                    "status": target,
                },
            )
            await self._repository.commit()
            return await self._repository.service_bundle(service)
        except Exception:
            await self._repository.rollback()
            raise

    async def archive_service(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
    ) -> ServiceBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.service.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            service = await self._required_service(service_id, for_update=True)
            self._ensure_partner_ownership(service.partner_id, partner_id)
            ensure_catalog_transition(service.status, "archived")
            service.status = "archived"
            service.published_at = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.service.archived",
                resource_type="service_offering",
                resource_id=str(service.id),
            )
            await self._repository.commit()
            return await self._repository.service_bundle(service)
        except Exception:
            await self._repository.rollback()
            raise

    async def add_availability(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
        payload: CreateAvailabilityRequest,
    ) -> ServiceAvailability:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.availability.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            service = await self._required_service(service_id, for_update=True)
            self._ensure_partner_ownership(service.partner_id, partner_id)
            self._ensure_editable(service.status)
            if payload.professional_id is not None:
                professional = await self._repository.get_professional(payload.professional_id)
                if professional is None or professional.partner_id != partner_id:
                    raise AppError(
                        404,
                        "SERVICE_PROFESSIONAL_NOT_FOUND",
                        "Service professional not found",
                    )
            item = await self._repository.add_availability(
                partner_id=partner_id,
                service_id=service.id,
                values=payload.model_dump(),
            )
            if service.status == "published":
                service.status = "draft"
                service.published_at = None
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.availability.created",
                resource_type="service_availability",
                resource_id=str(item.id),
                metadata={"service_id": str(service.id)},
            )
            await self._repository.commit()
            return item
        except Exception:
            await self._repository.rollback()
            raise

    async def create_professional(
        self,
        *,
        actor: Actor,
        payload: CreateProfessionalRequest,
    ) -> ServiceProfessional:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.professional.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            professional = await self._repository.add_professional(
                partner_id=partner_id,
                values=payload.model_dump(),
            )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.professional.created",
                resource_type="service_professional",
                resource_id=str(professional.id),
            )
            await self._repository.commit()
            return professional
        except Exception:
            await self._repository.rollback()
            raise

    async def list_professionals(self, *, actor: Actor) -> list[ServiceProfessional]:
        partner_id = self._active_partner_id(actor)
        require_permission(actor, "catalog.service.read", partner_id=partner_id)
        return await self._repository.list_professionals(partner_id)

    async def assign_professional(
        self,
        *,
        actor: Actor,
        service_id: uuid.UUID,
        professional_id: uuid.UUID,
    ) -> ServiceBundle:
        partner_id = self._active_partner_id(actor)
        require_permission(
            actor,
            "catalog.professional.write",
            partner_id=partner_id,
            require_partner_write=True,
        )
        try:
            service = await self._required_service(service_id, for_update=True)
            self._ensure_partner_ownership(service.partner_id, partner_id)
            self._ensure_editable(service.status)
            professional = await self._repository.get_professional(professional_id)
            if professional is None or professional.partner_id != partner_id:
                raise AppError(
                    404,
                    "SERVICE_PROFESSIONAL_NOT_FOUND",
                    "Service professional not found",
                )
            await self._repository.assign_professional(
                partner_id=partner_id,
                service_id=service.id,
                professional_id=professional.id,
            )
            if service.status == "published":
                service.status = "draft"
                service.published_at = None
                service.review_reason = (
                    "Professional assignment changed; resubmission required."
                )
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=partner_id,
                action="catalog.professional.assigned",
                resource_type="service_offering",
                resource_id=str(service.id),
                metadata={"professional_id": str(professional.id)},
            )
            await self._repository.commit()
            return await self._repository.service_bundle(service)
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(
                409,
                "SERVICE_PROFESSIONAL_ALREADY_ASSIGNED",
                "Professional is already assigned to this service",
            ) from error
        except Exception:
            await self._repository.rollback()
            raise
