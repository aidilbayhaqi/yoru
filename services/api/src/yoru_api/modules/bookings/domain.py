import hashlib
import hmac
import secrets
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from yoru_api.core.problem import AppError


def create_booking_number(now: datetime, token: str | None = None) -> str:
    suffix = (token or secrets.token_hex(3)).upper()
    return f"YBK-{now:%Y%m%d}-{suffix}"


def ensure_timezone_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AppError(422, "BOOKING_TIMEZONE_REQUIRED", "Scheduled time must include timezone")


def local_schedule(
    scheduled_start: datetime,
    scheduled_end: datetime,
    timezone: str,
) -> tuple[int, time, time]:
    ensure_timezone_aware(scheduled_start)
    ensure_timezone_aware(scheduled_end)
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise AppError(422, "BOOKING_TIMEZONE_INVALID", "Booking timezone is invalid") from exc
    local_start = scheduled_start.astimezone(zone)
    local_end = scheduled_end.astimezone(zone)
    if local_end.date() != local_start.date():
        raise AppError(422, "BOOKING_CROSSES_DAY", "Booking cannot cross a local calendar day")
    return local_start.weekday(), local_start.timetz().replace(tzinfo=None), local_end.timetz().replace(tzinfo=None)


def schedule_is_covered(
    *,
    weekday: int,
    start_time: time,
    end_time: time,
    windows: list[tuple[int, time, time]],
) -> bool:
    return any(
        window_weekday == weekday
        and window_start <= start_time
        and window_end >= end_time
        for window_weekday, window_start, window_end in windows
    )


def hash_booking_otp(
    *,
    secret: str,
    booking_id: str,
    purpose: str,
    otp: str,
) -> str:
    material = f"yoru-booking-otp:v1:{booking_id}:{purpose}:{otp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


def verify_booking_otp(
    *,
    expected_hash: str,
    secret: str,
    booking_id: str,
    purpose: str,
    otp: str,
) -> bool:
    actual = hash_booking_otp(
        secret=secret,
        booking_id=booking_id,
        purpose=purpose,
        otp=otp,
    )
    return hmac.compare_digest(expected_hash, actual)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def ensure_coordinates(latitude: Decimal, longitude: Decimal) -> None:
    if not Decimal("-90") <= latitude <= Decimal("90"):
        raise AppError(422, "TRACKING_LATITUDE_INVALID", "Latitude is outside valid range")
    if not Decimal("-180") <= longitude <= Decimal("180"):
        raise AppError(422, "TRACKING_LONGITUDE_INVALID", "Longitude is outside valid range")
