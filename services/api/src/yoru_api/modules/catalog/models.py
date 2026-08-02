import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from yoru_api.core.models import Base


class CatalogCategory(Base):
    __tablename__ = "catalog_categories"
    __table_args__ = (
        Index("ix_catalog_categories_active_name", "is_active", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Product(Base):
    __tablename__ = "catalog_products"
    __table_args__ = (
        UniqueConstraint("partner_id", "slug", name="uq_catalog_products_partner_slug"),
        UniqueConstraint("partner_id", "sku", name="uq_catalog_products_partner_sku"),
        Index("ix_catalog_products_public", "status", "category_id", "updated_at"),
        Index("ix_catalog_products_partner_status", "partner_id", "status"),
        CheckConstraint("unit_price >= 0", name="ck_catalog_products_price_nonnegative"),
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'published', "
            "'revision_required', 'rejected', 'archived')",
            name="ck_catalog_products_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    stock_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    review_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProductMedia(Base):
    __tablename__ = "catalog_product_media"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_catalog_product_media_object_key"),
        Index("ix_catalog_product_media_product_order", "product_id", "sort_order"),
        CheckConstraint("sort_order >= 0", name="ck_catalog_product_media_sort_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_inventory_items_product"),
        Index("ix_inventory_items_partner_updated", "partner_id", "updated_at"),
        CheckConstraint("on_hand >= 0", name="ck_inventory_items_on_hand_nonnegative"),
        CheckConstraint("reserved >= 0", name="ck_inventory_items_reserved_nonnegative"),
        CheckConstraint("reserved <= on_hand", name="ck_inventory_items_reserved_lte_on_hand"),
        CheckConstraint("reorder_level >= 0", name="ck_inventory_items_reorder_nonnegative"),
        CheckConstraint("version >= 1", name="ck_inventory_items_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


class ServiceOffering(Base):
    __tablename__ = "service_offerings"
    __table_args__ = (
        UniqueConstraint("partner_id", "slug", name="uq_service_offerings_partner_slug"),
        Index("ix_service_offerings_public", "status", "category_id", "updated_at"),
        Index("ix_service_offerings_partner_status", "partner_id", "status"),
        CheckConstraint("price >= 0", name="ck_service_offerings_price_nonnegative"),
        CheckConstraint(
            "duration_minutes BETWEEN 5 AND 1440",
            name="ck_service_offerings_duration_range",
        ),
        CheckConstraint(
            "capacity_per_slot BETWEEN 1 AND 10000",
            name="ck_service_offerings_capacity_range",
        ),
        CheckConstraint(
            "booking_notice_minutes >= 0",
            name="ck_service_offerings_booking_notice_nonnegative",
        ),
        CheckConstraint(
            "cancellation_window_minutes >= 0",
            name="ck_service_offerings_cancellation_nonnegative",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'published', "
            "'revision_required', 'rejected', 'archived')",
            name="ck_service_offerings_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    capacity_per_slot: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    booking_notice_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_window_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    review_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ServiceProfessional(Base):
    __tablename__ = "service_professionals"
    __table_args__ = (
        Index("ix_service_professionals_partner_active", "partner_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str | None] = mapped_column(String(160))
    bio: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ServiceProfessionalAssignment(Base):
    __tablename__ = "service_professional_assignments"
    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "professional_id",
            name="uq_service_professional_assignments_pair",
        ),
        Index(
            "ix_service_professional_assignments_professional",
            "professional_id",
            "service_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_professionals.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceAvailability(Base):
    __tablename__ = "service_availability"
    __table_args__ = (
        Index(
            "ix_service_availability_service_weekday",
            "service_id",
            "weekday",
            "start_time",
        ),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_service_availability_weekday"),
        CheckConstraint("end_time > start_time", name="ck_service_availability_time_order"),
        CheckConstraint(
            "slot_interval_minutes BETWEEN 5 AND 1440",
            name="ck_service_availability_interval_range",
        ),
        CheckConstraint(
            "capacity_override IS NULL OR capacity_override BETWEEN 1 AND 10000",
            name="ck_service_availability_capacity_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    professional_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_professionals.id", ondelete="CASCADE"),
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Jakarta"
    )
    slot_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    capacity_override: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
