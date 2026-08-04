from yoru_api.cli.demo_seed_data import (
    CATEGORIES,
    PARTNERS,
    PRODUCTS,
    PROFESSIONALS,
    SERVICES,
)


def test_demo_seed_has_expected_minimums() -> None:
    assert len(CATEGORIES) >= 9
    assert len(PARTNERS) >= 8
    assert len(PRODUCTS) >= 6
    assert len(PROFESSIONALS) >= 9
    assert len(SERVICES) >= 6


def test_product_slugs_and_media_are_unique() -> None:
    assert len({item.slug for item in PRODUCTS}) == len(PRODUCTS)
    assert len({item.image_path for item in PRODUCTS}) == len(PRODUCTS)
    assert all(item.image_path.startswith("/yoru-media/demo/") for item in PRODUCTS)


def test_service_professionals_exist() -> None:
    professional_keys = {item.key for item in PROFESSIONALS}
    for service in SERVICES:
        assert service.professional_keys
        assert set(service.professional_keys) <= professional_keys
