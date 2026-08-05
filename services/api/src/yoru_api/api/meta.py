from fastapi import APIRouter, Request

from yoru_api import __version__
from yoru_api.runtime_contract import RUNTIME_CONTRACT_VERSION, RUNTIME_STAGE

router = APIRouter(tags=["meta"])

CORE_BUSINESS_MODULES = frozenset(
    {
        "partners",
        "catalog",
        "commerce",
        "bookings",
        "finance",
    }
)


@router.get("/meta")
async def api_metadata(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    mounted_modules = tuple(getattr(request.app.state, "router_names", ()))
    mounted_module_set = set(mounted_modules)

    return {
        "name": "Yoru API",
        "version": __version__,
        "release_id": settings.release_id,
        "stage": RUNTIME_STAGE,
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "business_modules_enabled": CORE_BUSINESS_MODULES <= mounted_module_set,
        "modules": list(mounted_modules),
        "features": {
            "identity": "identity" in mounted_module_set,
            "mobile_identity": "mobile_identity" in mounted_module_set,
            "customer_ai": settings.feature_customer_ai,
            "partner_copilot": settings.feature_partner_copilot,
            "live_tracking": settings.feature_live_tracking,
            "dental_service": settings.feature_dental_service,
        },
    }
