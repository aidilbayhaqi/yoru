import pytest
from pydantic import ValidationError

from yoru_api.modules.commerce.schemas import QuoteRequest
from yoru_api.modules.commerce.shipping import build_shipping_quote


def _address() -> dict[str, object]:
    return {
        "recipient_name": "Ucok",
        "recipient_phone": "+628123456789",
        "address_line1": "Jl. Contoh No. 1",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "postal_code": "12345",
        "country_code": "ID",
    }


def test_pickup_remains_backward_compatible() -> None:
    payload = QuoteRequest()
    assert payload.fulfillment_type == "pickup"
    assert payload.shipping_address is None


def test_shipping_request_requires_address_and_service() -> None:
    with pytest.raises(ValidationError):
        QuoteRequest(fulfillment_type="shipping")


def test_regular_shipping_quote_has_snapshot() -> None:
    quote = build_shipping_quote(
        fulfillment_type="shipping",
        shipping_service="regular",
        shipping_address=_address(),
        currency="IDR",
    )

    assert quote.amount == 20_000
    assert quote.address_snapshot is not None
    assert quote.address_snapshot["recipient_name"] == "Ucok"
    assert quote.method_snapshot["code"] == "regular"
    assert quote.method_snapshot["rate_version"] == "internal_flat_rate_v1"
