from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from yoru_api.core.problem import AppError


@dataclass(frozen=True, slots=True)
class ShippingQuote:
    amount: int
    currency: str
    address_snapshot: dict[str, object] | None
    method_snapshot: dict[str, object]


_OPTIONS: dict[str, dict[str, object]] = {
    "regular": {
        "code": "regular",
        "name": "Regular",
        "provider": "internal_flat_rate",
        "amount": 20_000,
        "currency": "IDR",
        "estimated_days_min": 2,
        "estimated_days_max": 5,
        "rate_version": "internal_flat_rate_v1",
    },
    "express": {
        "code": "express",
        "name": "Express",
        "provider": "internal_flat_rate",
        "amount": 35_000,
        "currency": "IDR",
        "estimated_days_min": 1,
        "estimated_days_max": 2,
        "rate_version": "internal_flat_rate_v1",
    },
    "same_day": {
        "code": "same_day",
        "name": "Same Day",
        "provider": "internal_flat_rate",
        "amount": 55_000,
        "currency": "IDR",
        "estimated_days_min": 0,
        "estimated_days_max": 1,
        "rate_version": "internal_flat_rate_v1",
    },
}


def available_shipping_options() -> list[dict[str, object]]:
    return [dict(option) for option in _OPTIONS.values()]


def _required_text(address: Mapping[str, Any], key: str) -> str:
    value = str(address.get(key, "")).strip()
    if not value:
        raise AppError(
            422,
            "SHIPPING_ADDRESS_INVALID",
            f"Shipping address field '{key}' is required",
        )
    return value


def normalize_shipping_address(address: Mapping[str, Any]) -> dict[str, object]:
    country_code = str(address.get("country_code", "ID")).strip().upper()
    if country_code != "ID":
        raise AppError(
            422,
            "SHIPPING_COUNTRY_UNSUPPORTED",
            "This release only supports shipping destinations in Indonesia",
        )

    normalized: dict[str, object] = {
        "recipient_name": _required_text(address, "recipient_name"),
        "recipient_phone": _required_text(address, "recipient_phone"),
        "address_line1": _required_text(address, "address_line1"),
        "address_line2": str(address.get("address_line2", "")).strip() or None,
        "district": str(address.get("district", "")).strip() or None,
        "city": _required_text(address, "city"),
        "province": _required_text(address, "province"),
        "postal_code": _required_text(address, "postal_code"),
        "country_code": country_code,
        "delivery_note": str(address.get("delivery_note", "")).strip() or None,
    }

    latitude = address.get("latitude")
    longitude = address.get("longitude")
    normalized["latitude"] = float(latitude) if latitude is not None else None
    normalized["longitude"] = float(longitude) if longitude is not None else None
    return normalized


def build_shipping_quote(
    *,
    fulfillment_type: str,
    shipping_service: str | None,
    shipping_address: Mapping[str, Any] | None,
    currency: str,
) -> ShippingQuote:
    if fulfillment_type == "pickup":
        return ShippingQuote(
            amount=0,
            currency=currency,
            address_snapshot=None,
            method_snapshot={
                "type": "pickup",
                "code": "pickup",
                "name": "Store Pickup",
                "provider": "internal",
                "amount": 0,
                "currency": currency,
                "rate_version": "pickup_v1",
            },
        )

    if fulfillment_type != "shipping":
        raise AppError(422, "FULFILLMENT_TYPE_INVALID", "Fulfillment type is invalid")
    if shipping_service is None or shipping_address is None:
        raise AppError(
            422,
            "SHIPPING_DETAILS_REQUIRED",
            "Shipping service and address are required",
        )

    option = _OPTIONS.get(shipping_service)
    if option is None:
        raise AppError(422, "SHIPPING_SERVICE_INVALID", "Shipping service is invalid")
    if currency != option["currency"]:
        raise AppError(409, "SHIPPING_CURRENCY_UNSUPPORTED", "Shipping currency is unsupported")

    method_snapshot = dict(option)
    method_snapshot["type"] = "shipping"
    return ShippingQuote(
        amount=int(option["amount"]),
        currency=currency,
        address_snapshot=normalize_shipping_address(shipping_address),
        method_snapshot=method_snapshot,
    )
