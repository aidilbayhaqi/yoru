import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent, OutboxEvent
from yoru_api.modules.bookings.models import (
    Booking,
    BookingAssignment,
    BookingCompletionChecklist,
    BookingTrackingPing,
    BookingTrackingSession,
    BookingVerification,
    CustomerAddress,
)
from yoru_api.modules.catalog.models import (
    ServiceAvailability,
    ServiceOffering,
    ServiceProfessional,
    ServiceProfessionalAssignment,
)
from yoru_api.modules.commerce.models import Order


@dataclass(frozen=True, slots=True)
class BookingBundle:
    booking: Booking
    assignment: BookingAssignment | None
    tracking: BookingTrackingSession | None
    latest_ping: BookingTrackingPing | None


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_address(self, **values: object) -> CustomerAddress:
        address = CustomerAddress(**values)
        self._session.add(address)
        await self._session.flush()
        return address

    async def clear_default_addresses(self, customer_id: uuid.UUID) -> None:
        result = await self._session.scalars(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
            )
        )
        for address in result:
            address.is_default = False

    async def get_address(self, address_id: uuid.UUID) -> CustomerAddress | None:
        return await self._session.scalar(
            select(CustomerAddress).where(CustomerAddress.id == address_id)
        )

    async def list_addresses(self, customer_id: uuid.UUID) -> list[CustomerAddress]:
        result = await self._session.scalars(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        )
        return list(result)

    async def get_service(self, service_id: uuid.UUID) -> ServiceOffering | None:
        return await self._session.scalar(
            select(ServiceOffering).where(ServiceOffering.id == service_id)
        )

    async def list_availability(
        self,
        *,
        service_id: uuid.UUID,
        weekday: int,
    ) -> list[ServiceAvailability]:
        result = await self._session.scalars(
            select(ServiceAvailability)
            .where(
                ServiceAvailability.service_id == service_id,
                ServiceAvailability.weekday == weekday,
                ServiceAvailability.is_active.is_(True),
            )
            .order_by(ServiceAvailability.start_time.asc())
        )
        return list(result)

    async def count_schedule_conflicts(
        self,
        *,
        service_id: uuid.UUID | None,
        scheduled_start: datetime,
        scheduled_end: datetime,
        professional_id: uuid.UUID | None = None,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> int:
        statement = select(func.count(Booking.id)).where(
            Booking.status.in_(
                ("requested", "confirmed", "assigned", "on_the_way", "arrived", "in_progress")
            ),
            Booking.scheduled_start < scheduled_end,
            Booking.scheduled_end > scheduled_start,
        )
        if service_id is not None:
            statement = statement.where(Booking.service_id == service_id)
        if professional_id is not None:
            statement = statement.where(Booking.professional_id == professional_id)
        if exclude_booking_id is not None:
            statement = statement.where(Booking.id != exclude_booking_id)
        value = await self._session.scalar(statement)
        return int(value or 0)

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.scalar(select(Order).where(Order.id == order_id))

    async def add_booking(self, **values: object) -> Booking:
        booking = Booking(**values)
        self._session.add(booking)
        await self._session.flush()
        return booking

    async def get_booking(
        self,
        booking_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Booking | None:
        statement: Select[tuple[Booking]] = select(Booking).where(Booking.id == booking_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_bookings(
        self,
        *,
        customer_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        limit: int,
    ) -> list[Booking]:
        statement = select(Booking)
        if customer_id is not None:
            statement = statement.where(Booking.customer_id == customer_id)
        if partner_id is not None:
            statement = statement.where(Booking.partner_id == partner_id)
        result = await self._session.scalars(
            statement.order_by(Booking.created_at.desc(), Booking.id.desc()).limit(limit)
        )
        return list(result)

    async def get_professional(self, professional_id: uuid.UUID) -> ServiceProfessional | None:
        return await self._session.scalar(
            select(ServiceProfessional).where(ServiceProfessional.id == professional_id)
        )

    async def professional_supports_service(
        self,
        *,
        professional_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> bool:
        assignment_id = await self._session.scalar(
            select(ServiceProfessionalAssignment.id).where(
                ServiceProfessionalAssignment.professional_id == professional_id,
                ServiceProfessionalAssignment.service_id == service_id,
            )
        )
        return assignment_id is not None

    async def list_assignments(
        self,
        booking_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> list[BookingAssignment]:
        statement: Select[tuple[BookingAssignment]] = select(BookingAssignment).where(
            BookingAssignment.booking_id == booking_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.scalars(
            statement.order_by(BookingAssignment.created_at.desc())
        )
        return list(result)

    async def active_assignment(self, booking_id: uuid.UUID) -> BookingAssignment | None:
        return await self._session.scalar(
            select(BookingAssignment)
            .where(
                BookingAssignment.booking_id == booking_id,
                BookingAssignment.status.in_(("pending", "accepted")),
            )
            .order_by(BookingAssignment.created_at.desc())
            .limit(1)
        )

    async def add_assignment(self, **values: object) -> BookingAssignment:
        assignment = BookingAssignment(**values)
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def get_verification(
        self,
        *,
        booking_id: uuid.UUID,
        purpose: str,
        for_update: bool = False,
    ) -> BookingVerification | None:
        statement: Select[tuple[BookingVerification]] = select(BookingVerification).where(
            BookingVerification.booking_id == booking_id,
            BookingVerification.purpose == purpose,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_verification(self, **values: object) -> BookingVerification:
        verification = BookingVerification(**values)
        self._session.add(verification)
        await self._session.flush()
        return verification

    async def get_tracking_session(
        self,
        booking_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> BookingTrackingSession | None:
        statement: Select[tuple[BookingTrackingSession]] = select(
            BookingTrackingSession
        ).where(BookingTrackingSession.booking_id == booking_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def add_tracking_session(self, **values: object) -> BookingTrackingSession:
        tracking = BookingTrackingSession(**values)
        self._session.add(tracking)
        await self._session.flush()
        return tracking

    async def add_tracking_ping(self, **values: object) -> BookingTrackingPing:
        ping = BookingTrackingPing(**values)
        self._session.add(ping)
        await self._session.flush()
        return ping

    async def latest_tracking_ping(self, session_id: uuid.UUID) -> BookingTrackingPing | None:
        return await self._session.scalar(
            select(BookingTrackingPing)
            .where(BookingTrackingPing.session_id == session_id)
            .order_by(BookingTrackingPing.recorded_at.desc(), BookingTrackingPing.id.desc())
        )

    async def get_completion(self, booking_id: uuid.UUID) -> BookingCompletionChecklist | None:
        return await self._session.scalar(
            select(BookingCompletionChecklist).where(
                BookingCompletionChecklist.booking_id == booking_id
            )
        )

    async def add_completion(self, **values: object) -> BookingCompletionChecklist:
        completion = BookingCompletionChecklist(**values)
        self._session.add(completion)
        await self._session.flush()
        return completion

    async def booking_bundle(self, booking: Booking) -> BookingBundle:
        assignment = await self.active_assignment(booking.id)
        tracking = await self.get_tracking_session(booking.id)
        latest_ping = (
            await self.latest_tracking_ping(tracking.id)
            if tracking is not None
            else None
        )
        return BookingBundle(
            booking=booking,
            assignment=assignment,
            tracking=tracking,
            latest_ping=latest_ping,
        )

    def add_audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=partner_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    def add_outbox(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

    async def rollback(self) -> None:
        await self._session.rollback()
