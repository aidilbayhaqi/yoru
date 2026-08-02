from datetime import UTC, datetime, time
from decimal import Decimal

import pytest

from yoru_api.core.problem import AppError
from yoru_api.modules.bookings.domain import (
    create_booking_number,
    ensure_coordinates,
    hash_booking_otp,
    local_schedule,
    schedule_is_covered,
    verify_booking_otp,
)
from yoru_api.modules.bookings.state_machine import ensure_booking_transition


def test_booking_number_is_stable_with_token() -> None:
    value = create_booking_number(
        datetime(2026, 8, 1, 10, 30, tzinfo=UTC),
        token="a1b2c3",
    )
    assert value == "YBK-20260801-A1B2C3"


def test_otp_hash_is_domain_separated_and_verifiable() -> None:
    digest = hash_booking_otp(
        secret="test-secret-with-more-than-thirty-two-characters",
        booking_id="booking-1",
        purpose="check_in",
        otp="123456",
    )
    assert verify_booking_otp(
        expected_hash=digest,
        secret="test-secret-with-more-than-thirty-two-characters",
        booking_id="booking-1",
        purpose="check_in",
        otp="123456",
    )
    assert not verify_booking_otp(
        expected_hash=digest,
        secret="test-secret-with-more-than-thirty-two-characters",
        booking_id="booking-1",
        purpose="check_out",
        otp="123456",
    )


def test_schedule_coverage() -> None:
    assert schedule_is_covered(
        weekday=0,
        start_time=time(9, 0),
        end_time=time(10, 0),
        windows=[(0, time(8, 0), time(17, 0))],
    )
    assert not schedule_is_covered(
        weekday=0,
        start_time=time(7, 30),
        end_time=time(9, 0),
        windows=[(0, time(8, 0), time(17, 0))],
    )


def test_local_schedule_uses_requested_timezone() -> None:
    start = datetime.fromisoformat("2026-08-03T09:00:00+07:00")
    end = datetime.fromisoformat("2026-08-03T10:00:00+07:00")
    weekday, start_time, end_time = local_schedule(start, end, "Asia/Jakarta")
    assert weekday == 0
    assert start_time == time(9, 0)
    assert end_time == time(10, 0)


def test_local_schedule_rejects_naive_datetime() -> None:
    with pytest.raises(AppError) as captured:
        local_schedule(
            datetime(2026, 8, 3, 9, 0),
            datetime(2026, 8, 3, 10, 0),
            "Asia/Jakarta",
        )
    assert captured.value.code == "BOOKING_TIMEZONE_REQUIRED"


def test_booking_happy_path_state_transitions() -> None:
    states = [
        "requested",
        "confirmed",
        "assigned",
        "on_the_way",
        "arrived",
        "in_progress",
        "completed",
    ]
    for current, target in zip(states, states[1:]):
        ensure_booking_transition(current, target)


def test_booking_invalid_transition_is_rejected() -> None:
    with pytest.raises(AppError) as captured:
        ensure_booking_transition("requested", "completed")
    assert captured.value.code == "BOOKING_STATE_CONFLICT"


def test_tracking_coordinates_are_validated() -> None:
    ensure_coordinates(Decimal("-6.2000000"), Decimal("106.8166667"))
    with pytest.raises(AppError) as captured:
        ensure_coordinates(Decimal("91"), Decimal("106"))
    assert captured.value.code == "TRACKING_LATITUDE_INVALID"
