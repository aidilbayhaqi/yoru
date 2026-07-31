from fastapi import APIRouter

from yoru_api import __version__

router = APIRouter(tags=["meta"])


@router.get("/meta")
async def api_metadata() -> dict[str, object]:
    return {
        "name": "Yoru API",
        "version": __version__,
        "stage": "identity-foundation",
        "business_modules_enabled": False,
        "features": {
            "identity": True,
            "customer_ai": False,
            "partner_copilot": False,
            "live_tracking": False,
            "dental_service": False,
        },
    }
