import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from yoru_api.core.problem import AppError
from yoru_api.modules.bookings.domain import (
    create_booking_number,
    ensure_coordinates,
    generate_otp,
    hash_booking_otp,
    local_schedule,
    schedule_is_covered,
    verify_booking_otp,
)
from yoru_api.modules.bookings.models import (
    Booking,
    BookingAssignment,
    BookingTrackingPing,
    BookingTrackingSession,
    BookingVerification,
    CustomerAddress,
)
from yoru_api.modules.bookings.repository import BookingBundle, BookingRepository
from yoru_api.modules.bookings.schemas import (
    BookingCompleteRequest,
    BookingCreateRequest,
    CustomerAddressCreate,
    TrackingPingRequest,
)
from yoru_api.modules.bookings.state_machine import ensure_booking_transition
from yoru_api.modules.commerce.domain import to_minor_units
from yoru_api.modules.identity.permissions import Actor, require_permission

OTP_TTL = timedelta(minutes=10)
TERMINAL_STATUSES = frozenset({"completed", "cancelled", "no_show"})


class BookingService:
    def __init__(
        self,
        repository: BookingRepository,
        *,
        otp_secret: str,
        live_tracking_enabled: bool,
    ) -> None:
        self._repository = repository
        self._otp_secret = otp_secret
        self._live_tracking_enabled = live_tracking_enabled

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    async def create_address(
        self,
        *,
        actor: Actor,
        payload: CustomerAddressCreate,
    ) -> CustomerAddress:
        if payload.is_default:
            await self._repository.clear_default_addresses(actor.user_id)
        address = await self._repository.add_address(
            customer_id=actor.user_id,
            **payload.model_dump(),
        )
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=None,
            action="booking.address.created",
            resource_type="customer_address",
            resource_id=str(address.id),
        )
        await self._repository.commit()
        return address

    async def list_addresses(self, actor: Actor) -> list[CustomerAddress]:
        return await self._repository.list_addresses(actor.user_id)

    async def _required_booking(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        for_update: bool = False,
    ) -> Booking:
        booking = await self._repository.get_booking(booking_id, for_update=for_update)
        if booking is None:
            raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")
        if booking.customer_id == actor.user_id:
            return booking
        membership = actor.active_membership
        if membership is not None and membership.partner_id == booking.partner_id:
            return booking
        if "platform.booking.read" in actor.platform_permissions:
            return booking
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")

    @staticmethod
    def _require_partner_actor(actor: Actor, booking: Booking, permission: str) -> None:
        require_permission(
            actor,
            permission,
            partner_id=booking.partner_id,
            require_partner_write=True,
        )

    async def _bundle(self, booking: Booking) -> BookingBundle:
        return await self._repository.booking_bundle(booking)

    async def create_booking(
        self,
        *,
        actor: Actor,
        payload: BookingCreateRequest,
    ) -> BookingBundle:
        now = self._now()
        if payload.scheduled_start <= now:
            raise AppError(422, "BOOKING_TIME_IN_PAST", "Booking time must be in the future")
        service = await self._repository.get_service(payload.service_id)
        if service is None or service.status != "published":
            raise AppError(404, "SERVICE_NOT_FOUND", "Published service not found")
        address = await self._repository.get_address(payload.address_id)
        if address is None or address.customer_id != actor.user_id:
            raise AppError(404, "CUSTOMER_ADDRESS_NOT_FOUND", "Customer address not found")
        scheduled_end = payload.scheduled_start + timedelta(minutes=service.duration_minutes)
        weekday, start_time, end_time = local_schedule(
            payload.scheduled_start,
            scheduled_end,
            payload.timezone,
        )
        availability = [
            item
            for item in await self._repository.list_availability(
                service_id=service.id,
                weekday=weekday,
            )
            if item.timezone == payload.timezone
        ]
        windows = [(item.weekday, item.start_time, item.end_time) for item in availability]
        if not schedule_is_covered(
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            windows=windows,
        ):
            raise AppError(409, "BOOKING_SLOT_UNAVAILABLE", "Requested time is unavailable")
        covering = [
            item
            for item in availability
            if item.start_time <= start_time
            and item.end_time >= end_time
            and (
                (
                    start_time.hour * 60
                    + start_time.minute
                    - item.start_time.hour * 60
                    - item.start_time.minute
                )
                % item.slot_interval_minutes
                == 0
            )
        ]
        if not covering:
            raise AppError(
                409,
                "BOOKING_SLOT_INTERVAL_MISMATCH",
                "Requested time does not align with the service slot interval",
            )
        capacity = max(
            [item.capacity_override or service.capacity_per_slot for item in covering],
            default=service.capacity_per_slot,
        )
        conflict_count = await self._repository.count_schedule_conflicts(
            service_id=service.id,
            scheduled_start=payload.scheduled_start,
            scheduled_end=scheduled_end,
        )
        if conflict_count >= capacity:
            raise AppError(409, "BOOKING_CAPACITY_EXCEEDED", "Requested slot is fully booked")
        if payload.order_id is not None:
            order = await self._repository.get_order(payload.order_id)
            if (
                order is None
                or order.customer_id != actor.user_id
                or order.partner_id != service.partner_id
                or order.payment_status != "paid"
            ):
                raise AppError(409, "BOOKING_ORDER_INVALID", "Paid order is not valid for booking")
        booking = await self._repository.add_booking(
            number=create_booking_number(now),
            customer_id=actor.user_id,
            partner_id=service.partner_id,
            service_id=service.id,
            order_id=payload.order_id,
            address_id=address.id,
            status="requested",
            scheduled_start=payload.scheduled_start,
            scheduled_end=scheduled_end,
            timezone=payload.timezone,
            service_name=service.name,
            service_duration_minutes=service.duration_minutes,
            currency=service.currency,
            amount=to_minor_units(service.price),
            address_snapshot={
                "recipient_name": address.recipient_name,
                "phone": address.phone,
                "address_line1": address.address_line1,
                "address_line2": address.address_line2,
                "city": address.city,
                "province": address.province,
                "postal_code": address.postal_code,
                "latitude": str(address.latitude) if address.latitude is not None else None,
                "longitude": str(address.longitude) if address.longitude is not None else None,
            },
            customer_notes=payload.notes,
        )
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=booking.partner_id,
            action="booking.created",
            resource_type="booking",
            resource_id=str(booking.id),
            metadata={"service_id": str(service.id), "scheduled_start": str(booking.scheduled_start)},
        )
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="booking.created",
            payload={
                "booking_id": str(booking.id),
                "customer_id": str(actor.user_id),
                "partner_id": str(booking.partner_id),
            },
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def list_bookings(self, *, actor: Actor, limit: int) -> list[BookingBundle]:
        membership = actor.active_membership
        is_partner = membership is not None and "booking.manage" in actor.permissions
        is_platform = "platform.booking.read" in actor.platform_permissions
        bookings = await self._repository.list_bookings(
            customer_id=None if is_partner or is_platform else actor.user_id,
            partner_id=membership.partner_id if is_partner and membership is not None else None,
            limit=limit,
        )
        return [await self._bundle(booking) for booking in bookings]

    async def get_booking(self, *, actor: Actor, booking_id: uuid.UUID) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id)
        return await self._bundle(booking)

    async def confirm(self, *, actor: Actor, booking_id: uuid.UUID) -> BookingBundle:
        booking = await self._required_booking(
            actor=actor,
            booking_id=booking_id,
            for_update=True,
        )
        self._require_partner_actor(actor, booking, "booking.manage")
        ensure_booking_transition(booking.status, "confirmed")
        booking.status = "confirmed"
        booking.confirmed_at = self._now()
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="booking.confirmed",
            payload={"booking_id": str(booking.id)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def assign(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        professional_id: uuid.UUID,
        notes: str | None,
    ) -> BookingBundle:
        booking = await self._required_booking(
            actor=actor,
            booking_id=booking_id,
            for_update=True,
        )
        self._require_partner_actor(actor, booking, "booking.manage")
        if booking.status not in {"confirmed", "assigned"}:
            raise AppError(409, "BOOKING_STATE_CONFLICT", "Booking cannot be assigned")
        professional = await self._repository.get_professional(professional_id)
        if (
            professional is None
            or professional.partner_id != booking.partner_id
            or not professional.is_active
        ):
            raise AppError(404, "PROFESSIONAL_NOT_FOUND", "Professional not found")
        if not await self._repository.professional_supports_service(
            professional_id=professional.id,
            service_id=booking.service_id,
        ):
            raise AppError(409, "PROFESSIONAL_SERVICE_MISMATCH", "Professional cannot perform service")
        weekday, start_time, end_time = local_schedule(
            booking.scheduled_start,
            booking.scheduled_end,
            booking.timezone,
        )
        professional_windows = [
            item
            for item in await self._repository.list_availability(
                service_id=booking.service_id,
                weekday=weekday,
            )
            if item.timezone == booking.timezone
            and item.professional_id in {None, professional.id}
        ]
        if not schedule_is_covered(
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            windows=[
                (item.weekday, item.start_time, item.end_time)
                for item in professional_windows
            ],
        ):
            raise AppError(
                409,
                "PROFESSIONAL_AVAILABILITY_MISMATCH",
                "Professional is not available in the requested slot",
            )
        conflicts = await self._repository.count_schedule_conflicts(
            service_id=None,
            scheduled_start=booking.scheduled_start,
            scheduled_end=booking.scheduled_end,
            professional_id=professional.id,
            exclude_booking_id=booking.id,
        )
        if conflicts > 0:
            raise AppError(409, "PROFESSIONAL_UNAVAILABLE", "Professional has another booking")
        current = await self._repository.active_assignment(booking.id)
        if current is not None:
            current.status = "cancelled"
            current.responded_at = self._now()
            current.response_reason = "Reassigned"
        now = self._now()
        await self._repository.add_assignment(
            booking_id=booking.id,
            partner_id=booking.partner_id,
            professional_id=professional.id,
            assigned_by_user_id=actor.user_id,
            status="accepted",
            response_reason=notes,
            assigned_at=now,
            responded_at=now,
        )
        if booking.status == "confirmed":
            ensure_booking_transition(booking.status, "assigned")
        booking.status = "assigned"
        booking.professional_id = professional.id
        booking.assigned_at = now
        booking.partner_notes = notes
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="professional.assigned",
            payload={
                "booking_id": str(booking.id),
                "professional_id": str(professional.id),
            },
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def issue_verification(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        purpose: str,
    ) -> tuple[str, datetime]:
        booking = await self._required_booking(
            actor=actor,
            booking_id=booking_id,
            for_update=True,
        )
        if booking.customer_id != actor.user_id:
            raise AppError(403, "BOOKING_CUSTOMER_REQUIRED", "Only the customer can issue OTP")
        valid_statuses = {
            "check_in": {"assigned", "on_the_way", "arrived"},
            "check_out": {"in_progress"},
        }
        if purpose not in valid_statuses or booking.status not in valid_statuses[purpose]:
            raise AppError(409, "BOOKING_OTP_STATE_CONFLICT", "OTP cannot be issued now")
        otp = generate_otp()
        expires_at = self._now() + OTP_TTL
        otp_hash = hash_booking_otp(
            secret=self._otp_secret,
            booking_id=str(booking.id),
            purpose=purpose,
            otp=otp,
        )
        verification = await self._repository.get_verification(
            booking_id=booking.id,
            purpose=purpose,
            for_update=True,
        )
        if verification is None:
            await self._repository.add_verification(
                booking_id=booking.id,
                customer_id=booking.customer_id,
                purpose=purpose,
                otp_hash=otp_hash,
                attempts=0,
                max_attempts=5,
                expires_at=expires_at,
            )
        else:
            verification.otp_hash = otp_hash
            verification.attempts = 0
            verification.expires_at = expires_at
            verification.verified_at = None
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=booking.partner_id,
            action=f"booking.otp.{purpose}.issued",
            resource_type="booking",
            resource_id=str(booking.id),
        )
        await self._repository.commit()
        return otp, expires_at

    async def _verify_otp(self, *, booking: Booking, purpose: str, otp: str) -> BookingVerification:
        verification = await self._repository.get_verification(
            booking_id=booking.id,
            purpose=purpose,
            for_update=True,
        )
        now = self._now()
        if verification is None or verification.verified_at is not None:
            raise AppError(409, "BOOKING_OTP_REQUIRED", "A valid OTP must be issued")
        if verification.expires_at <= now:
            raise AppError(409, "BOOKING_OTP_EXPIRED", "OTP has expired")
        if verification.attempts >= verification.max_attempts:
            raise AppError(429, "BOOKING_OTP_LOCKED", "OTP attempts exceeded")
        verification.attempts += 1
        if not verify_booking_otp(
            expected_hash=verification.otp_hash,
            secret=self._otp_secret,
            booking_id=str(booking.id),
            purpose=purpose,
            otp=otp,
        ):
            await self._repository.commit()
            raise AppError(403, "BOOKING_OTP_INVALID", "OTP is invalid")
        verification.verified_at = now
        return verification

    async def start_trip(self, *, actor: Actor, booking_id: uuid.UUID) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        self._require_partner_actor(actor, booking, "booking.execute")
        if booking.professional_id is None:
            raise AppError(409, "BOOKING_PROFESSIONAL_REQUIRED", "Professional is not assigned")
        ensure_booking_transition(booking.status, "on_the_way")
        booking.status = "on_the_way"
        booking.started_trip_at = self._now()
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="booking.trip_started",
            payload={"booking_id": str(booking.id)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def arrive(self, *, actor: Actor, booking_id: uuid.UUID) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        self._require_partner_actor(actor, booking, "booking.execute")
        ensure_booking_transition(booking.status, "arrived")
        booking.status = "arrived"
        booking.arrived_at = self._now()
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="professional.arrived",
            payload={"booking_id": str(booking.id)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def start_service(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        otp: str,
    ) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        self._require_partner_actor(actor, booking, "booking.execute")
        ensure_booking_transition(booking.status, "in_progress")
        await self._verify_otp(booking=booking, purpose="check_in", otp=otp)
        booking.status = "in_progress"
        booking.started_at = self._now()
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="service.started",
            payload={"booking_id": str(booking.id)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def complete(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        payload: BookingCompleteRequest,
    ) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        self._require_partner_actor(actor, booking, "booking.execute")
        if booking.professional_id is None:
            raise AppError(409, "BOOKING_PROFESSIONAL_REQUIRED", "Professional is not assigned")
        ensure_booking_transition(booking.status, "completed")
        await self._verify_otp(booking=booking, purpose="check_out", otp=payload.otp)
        now = self._now()
        booking.status = "completed"
        booking.completed_at = now
        booking.version += 1
        assignment = await self._repository.active_assignment(booking.id)
        if assignment is not None:
            assignment.status = "completed"
            assignment.completed_at = now
        completion = await self._repository.get_completion(booking.id)
        if completion is None:
            await self._repository.add_completion(
                booking_id=booking.id,
                partner_id=booking.partner_id,
                professional_id=booking.professional_id,
                completed_by_user_id=actor.user_id,
                checklist=payload.checklist,
                notes=payload.notes,
                completed_at=now,
            )
        tracking = await self._repository.get_tracking_session(booking.id, for_update=True)
        if tracking is not None and tracking.status == "active":
            tracking.status = "stopped"
            tracking.stopped_at = now
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="service.completed",
            payload={"booking_id": str(booking.id)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def cancel(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        reason: str,
    ) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        is_customer = booking.customer_id == actor.user_id
        if not is_customer:
            self._require_partner_actor(actor, booking, "booking.manage")
        ensure_booking_transition(booking.status, "cancelled")
        if is_customer:
            service = await self._repository.get_service(booking.service_id)
            if service is not None:
                cutoff = booking.scheduled_start - timedelta(
                    minutes=service.cancellation_window_minutes
                )
                if self._now() > cutoff:
                    raise AppError(
                        409,
                        "BOOKING_CANCELLATION_WINDOW_CLOSED",
                        "Cancellation window has closed",
                    )
        now = self._now()
        booking.status = "cancelled"
        booking.cancellation_reason = reason
        booking.cancelled_by_user_id = actor.user_id
        booking.cancelled_at = now
        booking.version += 1
        assignment = await self._repository.active_assignment(booking.id)
        if assignment is not None:
            assignment.status = "cancelled"
            assignment.responded_at = now
            assignment.response_reason = reason
        tracking = await self._repository.get_tracking_session(booking.id, for_update=True)
        if tracking is not None and tracking.status == "active":
            tracking.status = "stopped"
            tracking.stopped_at = now
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="booking.cancelled",
            payload={"booking_id": str(booking.id), "reason": reason},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def no_show(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        reason: str,
    ) -> BookingBundle:
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        self._require_partner_actor(actor, booking, "booking.manage")
        ensure_booking_transition(booking.status, "no_show")
        booking.status = "no_show"
        booking.partner_notes = reason
        booking.no_show_at = self._now()
        booking.version += 1
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="booking.no_show",
            payload={"booking_id": str(booking.id), "reason": reason},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    def _ensure_tracking_enabled(self) -> None:
        if not self._live_tracking_enabled:
            raise AppError(404, "LIVE_TRACKING_DISABLED", "Live tracking feature is disabled")

    async def consent_tracking(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        ttl_minutes: int,
    ) -> BookingBundle:
        self._ensure_tracking_enabled()
        booking = await self._required_booking(actor=actor, booking_id=booking_id, for_update=True)
        if booking.customer_id != actor.user_id:
            raise AppError(403, "BOOKING_CUSTOMER_REQUIRED", "Only the customer can consent")
        if booking.status not in {"assigned", "on_the_way", "arrived", "in_progress"}:
            raise AppError(409, "TRACKING_STATE_CONFLICT", "Tracking cannot start now")
        if booking.professional_id is None:
            raise AppError(409, "BOOKING_PROFESSIONAL_REQUIRED", "Professional is not assigned")
        now = self._now()
        expires_at = now + timedelta(minutes=ttl_minutes)
        tracking = await self._repository.get_tracking_session(booking.id, for_update=True)
        if tracking is None:
            tracking = await self._repository.add_tracking_session(
                booking_id=booking.id,
                customer_id=booking.customer_id,
                partner_id=booking.partner_id,
                professional_id=booking.professional_id,
                status="active",
                consented_at=now,
                started_at=now,
                expires_at=expires_at,
            )
        else:
            tracking.professional_id = booking.professional_id
            tracking.status = "active"
            tracking.consented_at = now
            tracking.started_at = now
            tracking.expires_at = expires_at
            tracking.stopped_at = None
        self._repository.add_outbox(
            aggregate_type="booking",
            aggregate_id=str(booking.id),
            event_type="tracking.started",
            payload={"booking_id": str(booking.id), "expires_at": str(expires_at)},
        )
        await self._repository.commit()
        return await self._bundle(booking)

    async def add_tracking_ping(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
        payload: TrackingPingRequest,
    ) -> BookingTrackingPing:
        self._ensure_tracking_enabled()
        booking = await self._required_booking(actor=actor, booking_id=booking_id)
        self._require_partner_actor(actor, booking, "booking.tracking.write")
        if booking.professional_id != payload.professional_id:
            raise AppError(409, "TRACKING_PROFESSIONAL_MISMATCH", "Professional does not match")
        tracking = await self._repository.get_tracking_session(booking.id, for_update=True)
        now = self._now()
        if tracking is None or tracking.status != "active":
            raise AppError(409, "TRACKING_SESSION_INACTIVE", "Tracking session is inactive")
        if tracking.expires_at <= now:
            tracking.status = "expired"
            tracking.stopped_at = now
            await self._repository.commit()
            raise AppError(409, "TRACKING_SESSION_EXPIRED", "Tracking session has expired")
        ensure_coordinates(payload.latitude, payload.longitude)
        ping = await self._repository.add_tracking_ping(
            booking_id=booking.id,
            session_id=tracking.id,
            professional_id=payload.professional_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            heading_degrees=payload.heading_degrees,
            speed_mps=payload.speed_mps,
            recorded_at=payload.recorded_at,
        )
        await self._repository.commit()
        return ping

    async def latest_location(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
    ) -> BookingTrackingPing:
        self._ensure_tracking_enabled()
        booking = await self._required_booking(actor=actor, booking_id=booking_id)
        tracking = await self._repository.get_tracking_session(booking.id)
        if tracking is None:
            raise AppError(404, "TRACKING_SESSION_NOT_FOUND", "Tracking session not found")
        ping = await self._repository.latest_tracking_ping(tracking.id)
        if ping is None:
            raise AppError(404, "TRACKING_LOCATION_NOT_FOUND", "No location is available")
        return ping

    async def stop_tracking(
        self,
        *,
        actor: Actor,
        booking_id: uuid.UUID,
    ) -> BookingBundle:
        self._ensure_tracking_enabled()
        booking = await self._required_booking(actor=actor, booking_id=booking_id)
        if booking.customer_id != actor.user_id:
            self._require_partner_actor(actor, booking, "booking.tracking.write")
        tracking = await self._repository.get_tracking_session(booking.id, for_update=True)
        if tracking is None:
            raise AppError(404, "TRACKING_SESSION_NOT_FOUND", "Tracking session not found")
        if tracking.status == "active":
            tracking.status = "stopped"
            tracking.stopped_at = self._now()
        await self._repository.commit()
        return await self._bundle(booking)
