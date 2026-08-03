import json
import logging
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from yoru_worker.settings import WorkerSettings

logger = logging.getLogger("yoru_worker")

# A transaction-scoped PostgreSQL advisory lock prevents two worker replicas from
# applying the same lifecycle transition in the same cycle.
_BOOKING_MAINTENANCE_LOCK = 8_906_425_917


@dataclass(frozen=True, slots=True)
class BookingMaintenanceStats:
    tracking_sessions_expired: int = 0
    otp_secrets_scrubbed: int = 0
    tracking_pings_deleted: int = 0
    requested_bookings_cancelled: int = 0
    bookings_marked_no_show: int = 0


class BookingMaintenanceJob:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )

    @property
    def name(self) -> str:
        return "booking-maintenance"

    async def close(self) -> None:
        await self._engine.dispose()

    async def run_once(self) -> BookingMaintenanceStats:
        async with self._engine.begin() as connection:
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
                {"lock_key": _BOOKING_MAINTENANCE_LOCK},
            )
            if not acquired:
                logger.info("booking_maintenance_skipped_lock_busy")
                return BookingMaintenanceStats()

            expired_tracking = await self._expire_tracking_sessions(connection)
            scrubbed_otps = await self._scrub_expired_otp_secrets(connection)
            deleted_pings = await self._delete_old_tracking_pings(connection)

            cancelled_requested = 0
            marked_no_show = 0
            if self._settings.booking_auto_no_show_enabled:
                cancelled_requested, marked_no_show = await self._release_stale_bookings(
                    connection
                )

            stats = BookingMaintenanceStats(
                tracking_sessions_expired=expired_tracking,
                otp_secrets_scrubbed=scrubbed_otps,
                tracking_pings_deleted=deleted_pings,
                requested_bookings_cancelled=cancelled_requested,
                bookings_marked_no_show=marked_no_show,
            )
            logger.info("booking_maintenance_completed", extra=asdict(stats))
            return stats

    async def _expire_tracking_sessions(self, connection: AsyncConnection) -> int:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT id, booking_id, partner_id
                    FROM booking_tracking_sessions
                    WHERE status = 'active' AND expires_at <= now()
                    ORDER BY expires_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT :batch_size
                    """
                ),
                {"batch_size": self._settings.booking_maintenance_batch_size},
            )
        ).mappings().all()

        changed = 0
        for row in rows:
            result = await connection.execute(
                text(
                    """
                    UPDATE booking_tracking_sessions
                    SET status = 'expired',
                        stopped_at = COALESCE(stopped_at, now()),
                        updated_at = now()
                    WHERE id = :id AND status = 'active'
                    """
                ),
                {"id": row["id"]},
            )
            if result.rowcount != 1:
                continue
            changed += 1
            await self._insert_audit(
                connection,
                partner_id=row["partner_id"],
                action="booking.tracking.expired",
                resource_type="booking_tracking_session",
                resource_id=str(row["id"]),
                metadata={"booking_id": str(row["booking_id"]), "source": "worker"},
            )
            await self._insert_outbox(
                connection,
                aggregate_type="booking",
                aggregate_id=str(row["booking_id"]),
                event_type="booking.tracking.expired",
                payload={
                    "booking_id": str(row["booking_id"]),
                    "tracking_session_id": str(row["id"]),
                    "partner_id": str(row["partner_id"]),
                },
            )
        return changed

    async def _scrub_expired_otp_secrets(self, connection: AsyncConnection) -> int:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT verification.id,
                           verification.booking_id,
                           verification.purpose,
                           booking.partner_id
                    FROM booking_verifications AS verification
                    JOIN bookings AS booking ON booking.id = verification.booking_id
                    WHERE verification.verified_at IS NULL
                      AND verification.expires_at <= now()
                      AND verification.otp_hash <> repeat('0', 64)
                    ORDER BY verification.expires_at, verification.id
                    FOR UPDATE OF verification SKIP LOCKED
                    LIMIT :batch_size
                    """
                ),
                {"batch_size": self._settings.booking_maintenance_batch_size},
            )
        ).mappings().all()

        changed = 0
        for row in rows:
            result = await connection.execute(
                text(
                    """
                    UPDATE booking_verifications
                    SET otp_hash = repeat('0', 64),
                        attempts = max_attempts,
                        updated_at = now()
                    WHERE id = :id
                      AND verified_at IS NULL
                      AND expires_at <= now()
                      AND otp_hash <> repeat('0', 64)
                    """
                ),
                {"id": row["id"]},
            )
            if result.rowcount != 1:
                continue
            changed += 1
            await self._insert_audit(
                connection,
                partner_id=row["partner_id"],
                action="booking.otp.expired",
                resource_type="booking_verification",
                resource_id=str(row["id"]),
                metadata={
                    "booking_id": str(row["booking_id"]),
                    "purpose": row["purpose"],
                    "source": "worker",
                },
            )
        return changed

    async def _delete_old_tracking_pings(self, connection: AsyncConnection) -> int:
        result = await connection.execute(
            text(
                """
                WITH candidates AS (
                    SELECT ping.id
                    FROM booking_tracking_pings AS ping
                    JOIN booking_tracking_sessions AS session
                      ON session.id = ping.session_id
                    WHERE session.status <> 'active'
                      AND ping.recorded_at < now() - (
                        :retention_days * interval '1 day'
                      )
                    ORDER BY ping.recorded_at, ping.id
                    LIMIT :batch_size
                    FOR UPDATE OF ping SKIP LOCKED
                )
                DELETE FROM booking_tracking_pings AS ping
                USING candidates
                WHERE ping.id = candidates.id
                """
            ),
            {
                "retention_days": self._settings.booking_tracking_ping_retention_days,
                "batch_size": self._settings.booking_maintenance_batch_size,
            },
        )
        return max(result.rowcount or 0, 0)

    async def _release_stale_bookings(
        self,
        connection: AsyncConnection,
    ) -> tuple[int, int]:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT id, partner_id, status
                    FROM bookings
                    WHERE status IN ('requested', 'confirmed', 'assigned')
                      AND scheduled_end <= now() - (
                        :grace_minutes * interval '1 minute'
                      )
                    ORDER BY scheduled_end, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT :batch_size
                    """
                ),
                {
                    "grace_minutes": self._settings.booking_auto_no_show_grace_minutes,
                    "batch_size": self._settings.booking_maintenance_batch_size,
                },
            )
        ).mappings().all()

        requested_cancelled = 0
        marked_no_show = 0
        for row in rows:
            previous_status = str(row["status"])
            target_status = "cancelled" if previous_status == "requested" else "no_show"
            result = await connection.execute(
                text(
                    """
                    UPDATE bookings
                    SET status = :target_status,
                        cancelled_at = CASE
                            WHEN :target_status = 'cancelled' THEN now()
                            ELSE cancelled_at
                        END,
                        cancellation_reason = CASE
                            WHEN :target_status = 'cancelled'
                            THEN 'Expired automatically after the scheduled window'
                            ELSE cancellation_reason
                        END,
                        no_show_at = CASE
                            WHEN :target_status = 'no_show' THEN now()
                            ELSE no_show_at
                        END,
                        version = version + 1,
                        updated_at = now()
                    WHERE id = :id AND status = :previous_status
                    """
                ),
                {
                    "id": row["id"],
                    "previous_status": previous_status,
                    "target_status": target_status,
                },
            )
            if result.rowcount != 1:
                continue

            await connection.execute(
                text(
                    """
                    UPDATE booking_assignments
                    SET status = 'cancelled',
                        response_reason = COALESCE(
                            response_reason,
                            'Booking lifecycle closed automatically by worker'
                        ),
                        responded_at = COALESCE(responded_at, now())
                    WHERE booking_id = :booking_id
                      AND status IN ('pending', 'accepted')
                    """
                ),
                {"booking_id": row["id"]},
            )
            await connection.execute(
                text(
                    """
                    UPDATE booking_tracking_sessions
                    SET status = 'expired',
                        stopped_at = COALESCE(stopped_at, now()),
                        updated_at = now()
                    WHERE booking_id = :booking_id AND status = 'active'
                    """
                ),
                {"booking_id": row["id"]},
            )

            event_type = (
                "booking.cancelled.expired"
                if target_status == "cancelled"
                else "booking.no_show.auto"
            )
            await self._insert_audit(
                connection,
                partner_id=row["partner_id"],
                action=event_type,
                resource_type="booking",
                resource_id=str(row["id"]),
                metadata={
                    "previous_status": previous_status,
                    "target_status": target_status,
                    "source": "worker",
                    "grace_minutes": self._settings.booking_auto_no_show_grace_minutes,
                },
            )
            await self._insert_outbox(
                connection,
                aggregate_type="booking",
                aggregate_id=str(row["id"]),
                event_type=event_type,
                payload={
                    "booking_id": str(row["id"]),
                    "partner_id": str(row["partner_id"]),
                    "previous_status": previous_status,
                    "status": target_status,
                },
            )
            if target_status == "cancelled":
                requested_cancelled += 1
            else:
                marked_no_show += 1
        return requested_cancelled, marked_no_show

    @staticmethod
    async def _insert_audit(
        connection: AsyncConnection,
        *,
        partner_id: object,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any],
    ) -> None:
        await connection.execute(
            text(
                """
                INSERT INTO audit_events (
                    id, actor_id, partner_id, action,
                    resource_type, resource_id, metadata, created_at
                )
                VALUES (
                    :id, NULL, :partner_id, :action,
                    :resource_type, :resource_id, CAST(:metadata AS jsonb), now()
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "partner_id": partner_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": json.dumps(metadata),
            },
        )

    @staticmethod
    async def _insert_outbox(
        connection: AsyncConnection,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        await connection.execute(
            text(
                """
                INSERT INTO outbox_events (
                    id, aggregate_type, aggregate_id,
                    event_type, payload, created_at, published_at
                )
                VALUES (
                    :id, :aggregate_type, :aggregate_id,
                    :event_type, CAST(:payload AS jsonb), now(), NULL
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_type": event_type,
                "payload": json.dumps(payload),
            },
        )
