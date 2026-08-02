from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.modules.catalog.repository import (
    CatalogRepository,
    ProductBundle,
    ServiceBundle,
)
from yoru_api.modules.catalog.schemas import (
    AvailabilityResponse,
    CategoryResponse,
    CreateAvailabilityRequest,
    CreateProductRequest,
    CreateProfessionalRequest,
    CreateServiceRequest,
    InventoryResponse,
    ModerationRequest,
    ProductListResponse,
    ProductMediaResponse,
    ProductResponse,
    ProfessionalResponse,
    RegisterProductMediaRequest,
    ServiceListResponse,
    ServiceResponse,
    UpdateInventoryRequest,
    UpdateProductRequest,
    UpdateServiceRequest,
)
from yoru_api.modules.catalog.service import CatalogService
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.security import constant_time_equal

router = APIRouter(tags=["Catalog, services, and inventory"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_catalog_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CatalogService:
    return CatalogService(CatalogRepository(session))


CatalogServiceDependency = Annotated[CatalogService, Depends(get_catalog_service)]


def _validate_csrf(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin is not None and origin not in request.app.state.settings.cors_allowed_origins:
        raise AppError(403, "ORIGIN_DENIED", "Request origin is not allowed")
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not constant_time_equal(
        cookie_token,
        header_token,
    ):
        raise AppError(403, "CSRF_VALIDATION_FAILED", "CSRF validation failed")


def _product_response(
    bundle: ProductBundle,
    *,
    include_inventory: bool = True,
) -> ProductResponse:
    response = ProductResponse.model_validate(bundle.product)
    return response.model_copy(
        update={
            "available_quantity": (
                bundle.inventory.available
                if bundle.product.stock_tracked and bundle.inventory is not None
                else None
            ),
            "inventory": (
                InventoryResponse.model_validate(bundle.inventory)
                if include_inventory
                and bundle.product.stock_tracked
                and bundle.inventory is not None
                else None
            ),
            "media": [ProductMediaResponse.model_validate(item) for item in bundle.media],
        }
    )


def _service_response(bundle: ServiceBundle) -> ServiceResponse:
    response = ServiceResponse.model_validate(bundle.service)
    return response.model_copy(
        update={
            "availability": [
                AvailabilityResponse.model_validate(item) for item in bundle.availability
            ],
            "professionals": [
                ProfessionalResponse.model_validate(item) for item in bundle.professionals
            ],
        }
    )


@router.get("/catalog/categories", response_model=list[CategoryResponse])
async def list_categories(
    service: CatalogServiceDependency,
) -> list[CategoryResponse]:
    categories = await service.list_categories()
    return [CategoryResponse.model_validate(item) for item in categories]


@router.get("/catalog/products", response_model=ProductListResponse)
async def list_public_products(
    service: CatalogServiceDependency,
    category_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> ProductListResponse:
    bundles = await service.list_public_products(category_id=category_id, limit=limit)
    return ProductListResponse(
        data=[_product_response(bundle, include_inventory=False) for bundle in bundles]
    )


@router.get("/catalog/products/{product_id}", response_model=ProductResponse)
async def get_public_product(
    product_id: UUID,
    service: CatalogServiceDependency,
) -> ProductResponse:
    return _product_response(
        await service.get_public_product(product_id),
        include_inventory=False,
    )


@router.get("/catalog/services", response_model=ServiceListResponse)
async def list_public_services(
    service: CatalogServiceDependency,
    category_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> ServiceListResponse:
    bundles = await service.list_public_services(category_id=category_id, limit=limit)
    return ServiceListResponse(data=[_service_response(bundle) for bundle in bundles])


@router.get("/catalog/services/{service_id}", response_model=ServiceResponse)
async def get_public_service(
    service_id: UUID,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    return _service_response(await service.get_public_service(service_id))


@router.get("/partner/catalog/products", response_model=ProductListResponse)
async def list_partner_products(
    actor: CurrentActor,
    service: CatalogServiceDependency,
    limit: int = Query(default=100, ge=1, le=200),
) -> ProductListResponse:
    bundles = await service.list_partner_products(actor=actor, limit=limit)
    return ProductListResponse(data=[_product_response(bundle) for bundle in bundles])


@router.post(
    "/partner/catalog/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: CreateProductRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductResponse:
    _validate_csrf(request)
    return _product_response(await service.create_product(actor=actor, payload=payload))


@router.patch("/partner/catalog/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    payload: UpdateProductRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductResponse:
    _validate_csrf(request)
    bundle = await service.update_product(
        actor=actor,
        product_id=product_id,
        payload=payload,
    )
    return _product_response(bundle)


@router.post(
    "/partner/catalog/products/{product_id}/media",
    response_model=ProductMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_product_media(
    product_id: UUID,
    payload: RegisterProductMediaRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductMediaResponse:
    _validate_csrf(request)
    item = await service.register_product_media(
        actor=actor,
        product_id=product_id,
        payload=payload,
    )
    return ProductMediaResponse.model_validate(item)


@router.post(
    "/partner/catalog/products/{product_id}/submit",
    response_model=ProductResponse,
)
async def submit_product(
    product_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductResponse:
    _validate_csrf(request)
    return _product_response(await service.submit_product(actor=actor, product_id=product_id))


@router.post(
    "/partner/catalog/products/{product_id}/archive",
    response_model=ProductResponse,
)
async def archive_product(
    product_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductResponse:
    _validate_csrf(request)
    return _product_response(await service.archive_product(actor=actor, product_id=product_id))


@router.put(
    "/partner/catalog/products/{product_id}/inventory",
    response_model=InventoryResponse,
)
async def update_inventory(
    product_id: UUID,
    payload: UpdateInventoryRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> InventoryResponse:
    _validate_csrf(request)
    item = await service.update_inventory(
        actor=actor,
        product_id=product_id,
        payload=payload,
    )
    return InventoryResponse.model_validate(item)


@router.get("/partner/catalog/services", response_model=ServiceListResponse)
async def list_partner_services(
    actor: CurrentActor,
    service: CatalogServiceDependency,
    limit: int = Query(default=100, ge=1, le=200),
) -> ServiceListResponse:
    bundles = await service.list_partner_services(actor=actor, limit=limit)
    return ServiceListResponse(data=[_service_response(bundle) for bundle in bundles])


@router.post(
    "/partner/catalog/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    payload: CreateServiceRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    return _service_response(await service.create_service(actor=actor, payload=payload))


@router.patch("/partner/catalog/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    payload: UpdateServiceRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    bundle = await service.update_service(
        actor=actor,
        service_id=service_id,
        payload=payload,
    )
    return _service_response(bundle)


@router.post(
    "/partner/catalog/services/{service_id}/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_availability(
    service_id: UUID,
    payload: CreateAvailabilityRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> AvailabilityResponse:
    _validate_csrf(request)
    item = await service.add_availability(
        actor=actor,
        service_id=service_id,
        payload=payload,
    )
    return AvailabilityResponse.model_validate(item)


@router.post(
    "/partner/catalog/services/{service_id}/submit",
    response_model=ServiceResponse,
)
async def submit_service(
    service_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    return _service_response(await service.submit_service(actor=actor, service_id=service_id))


@router.post(
    "/partner/catalog/services/{service_id}/archive",
    response_model=ServiceResponse,
)
async def archive_service(
    service_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    return _service_response(await service.archive_service(actor=actor, service_id=service_id))


@router.get(
    "/partner/catalog/professionals",
    response_model=list[ProfessionalResponse],
)
async def list_professionals(
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> list[ProfessionalResponse]:
    items = await service.list_professionals(actor=actor)
    return [ProfessionalResponse.model_validate(item) for item in items]


@router.post(
    "/partner/catalog/professionals",
    response_model=ProfessionalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_professional(
    payload: CreateProfessionalRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProfessionalResponse:
    _validate_csrf(request)
    item = await service.create_professional(actor=actor, payload=payload)
    return ProfessionalResponse.model_validate(item)


@router.post(
    "/partner/catalog/services/{service_id}/professionals/{professional_id}",
    response_model=ServiceResponse,
)
async def assign_professional(
    service_id: UUID,
    professional_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    bundle = await service.assign_professional(
        actor=actor,
        service_id=service_id,
        professional_id=professional_id,
    )
    return _service_response(bundle)


@router.get("/admin/catalog/products", response_model=ProductListResponse)
async def list_products_for_review(
    actor: CurrentActor,
    service: CatalogServiceDependency,
    item_status: str | None = Query(default="pending_review", alias="status", max_length=30),
    limit: int = Query(default=100, ge=1, le=200),
) -> ProductListResponse:
    bundles = await service.list_review_products(
        actor=actor,
        status=item_status,
        limit=limit,
    )
    return ProductListResponse(data=[_product_response(bundle) for bundle in bundles])


@router.post(
    "/admin/catalog/products/{product_id}/moderate",
    response_model=ProductResponse,
)
async def moderate_product(
    product_id: UUID,
    payload: ModerationRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ProductResponse:
    _validate_csrf(request)
    bundle = await service.moderate_product(
        actor=actor,
        product_id=product_id,
        payload=payload,
    )
    return _product_response(bundle)


@router.get("/admin/catalog/services", response_model=ServiceListResponse)
async def list_services_for_review(
    actor: CurrentActor,
    service: CatalogServiceDependency,
    item_status: str | None = Query(default="pending_review", alias="status", max_length=30),
    limit: int = Query(default=100, ge=1, le=200),
) -> ServiceListResponse:
    bundles = await service.list_review_services(
        actor=actor,
        status=item_status,
        limit=limit,
    )
    return ServiceListResponse(data=[_service_response(bundle) for bundle in bundles])


@router.post(
    "/admin/catalog/services/{service_id}/moderate",
    response_model=ServiceResponse,
)
async def moderate_service(
    service_id: UUID,
    payload: ModerationRequest,
    request: Request,
    actor: CurrentActor,
    service: CatalogServiceDependency,
) -> ServiceResponse:
    _validate_csrf(request)
    bundle = await service.moderate_service(
        actor=actor,
        service_id=service_id,
        payload=payload,
    )
    return _service_response(bundle)
