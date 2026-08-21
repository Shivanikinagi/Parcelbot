"""Core logistics domain: orders (shipments), tickets, and agreements.

Fields mirror the assessment workbook. Business timestamps (``booked_at``,
``created_at`` on tickets, etc.) are stored timezone-aware in Asia/Kolkata and
are distinct from the row's audit ``created_at``/``updated_at``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Account


class Order(Base, TimestampMixin):
    """A parcel/shipment. Status lifecycle: DRAFT → BOOKED → PICKED_UP → DELIVERED."""

    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("code", name="uq_orders_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # ORD-1001
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    carrier: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="BOOKED")
    booked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_actual_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipment_fee_inr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carrier_fault: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_fault: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    account: Mapped["Account"] = relationship(back_populates="orders")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")


class Ticket(Base, TimestampMixin):
    """A support case.

    ``severity`` is intentionally nullable: the source data does NOT include it.
    The agent classifies P1/P2/P3 from the description per the current Support
    Policy, and the SLA is then derived from the account's agreement or the
    policy defaults. ``historical_resolution`` is *context only* and may be wrong.
    """

    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("code", name="uq_tickets_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # TKT-501
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    business_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    assigned_to: Mapped[str | None] = mapped_column(String(120))
    last_customer_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Historical context only — NOT authoritative. May contain wrong guidance.
    historical_resolution: Mapped[str | None] = mapped_column(Text)
    #: Optionally persisted classification (the agent recomputes live too).
    severity: Mapped[str | None] = mapped_column(String(8))

    account: Mapped["Account"] = relationship(back_populates="tickets")
    order: Mapped["Order | None"] = relationship(back_populates="tickets")


class Agreement(Base, TimestampMixin):
    """A per-account contract — the single most authoritative knowledge source.

    ``terms`` holds the machine-readable SLA + cancellation + service-credit
    overrides that services read directly; ``body`` is the human-readable text,
    also chunked into the knowledge base for retrieval and citation.
    """

    __tablename__ = "agreements"
    __table_args__ = (UniqueConstraint("code", name="uq_agreements_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    #: "current" | "deprecated" — deprecated agreements never win a conflict.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_file: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    terms: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    account: Mapped["Account"] = relationship(back_populates="agreements")
