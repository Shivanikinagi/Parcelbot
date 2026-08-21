"""Domain enums and the source-authority hierarchy.

The :class:`SourceType` ordering is the heart of conflict resolution: when two
pieces of evidence disagree, the one with the higher authority (lower rank)
wins, tempered by freshness. Deprecated material never overrides current
material — it can only *explain* a conflict.
"""

from __future__ import annotations

from enum import Enum, IntEnum


class SourceType(str, Enum):
    """Knowledge sources, most authoritative first (see :data:`SOURCE_AUTHORITY`)."""

    CUSTOMER_AGREEMENT = "customer_agreement"
    POLICY = "policy"
    SOP = "sop"
    OPERATIONAL_GUIDE = "operational_guide"
    STRUCTURED_DATA = "structured_data"
    HISTORICAL_TICKET = "historical_ticket"
    DEPRECATED = "deprecated"


# Rank 1 == most authoritative. Used directly as a ranking weight.
SOURCE_AUTHORITY: dict[SourceType, int] = {
    SourceType.CUSTOMER_AGREEMENT: 1,
    SourceType.POLICY: 2,
    SourceType.SOP: 3,
    SourceType.OPERATIONAL_GUIDE: 4,
    SourceType.STRUCTURED_DATA: 5,
    SourceType.HISTORICAL_TICKET: 6,
    SourceType.DEPRECATED: 7,
}

MAX_AUTHORITY_RANK = max(SOURCE_AUTHORITY.values())


def authority_weight(source_type: SourceType) -> float:
    """Normalise authority to ``(0, 1]`` — higher means more trustworthy."""
    rank = SOURCE_AUTHORITY.get(source_type, MAX_AUTHORITY_RANK)
    return (MAX_AUTHORITY_RANK - rank + 1) / MAX_AUTHORITY_RANK


class TicketSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class OrderStatus(str, Enum):
    CREATED = "created"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    LOST = "lost"
    DAMAGED = "damaged"
    RETURNED = "returned"


class EscalationStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AccountTier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Carrier(str, Enum):
    SWIFTPOST = "SwiftPost"
    AEROCARGO = "AeroCargo"
    METROLINE = "MetroLine"
    GLOBALEX = "GlobalEx"


class Confidence(IntEnum):
    """Bucketed confidence for UI badges; the agent also emits a 0-1 score."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def from_score(cls, score: float) -> "Confidence":
        if score >= 0.75:
            return cls.HIGH
        if score >= 0.45:
            return cls.MEDIUM
        return cls.LOW


# Actions that mutate state and therefore REQUIRE explicit confirmation.
STATE_CHANGING_ACTIONS: frozenset[str] = frozenset(
    {"create_escalation", "create_follow_up_task", "update_ticket"}
)
