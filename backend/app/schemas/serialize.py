"""ORM → dict serializers shared by the tool layer and the API layer."""

from __future__ import annotations

from datetime import datetime

from app.models.logistics import Agreement, Order, Ticket
from app.models.organization import Account
from app.models.workflow import Escalation, FollowUpTask


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def account_to_dict(a: Account) -> dict:
    return {
        "code": a.code,
        "name": a.name,
        "plan": a.plan,
        "status": a.status,
        "csm": a.csm,
        "premium_support": a.premium_support,
        "health_score": a.health_score,
        "notes": a.notes,
    }


def order_to_dict(o: Order) -> dict:
    return {
        "code": o.code,
        "account_code": o.account.code if o.account else None,
        "carrier": o.carrier,
        "status": o.status,
        "booked_at": _iso(o.booked_at),
        "pickup_window_start": _iso(o.pickup_window_start),
        "pickup_window_end": _iso(o.pickup_window_end),
        "pickup_actual_at": _iso(o.pickup_actual_at),
        "shipment_fee_inr": o.shipment_fee_inr,
        "carrier_fault": o.carrier_fault,
        "customer_fault": o.customer_fault,
        "cancellation_requested_at": _iso(o.cancellation_requested_at),
        "notes": o.notes,
    }


def ticket_to_dict(t: Ticket) -> dict:
    return {
        "code": t.code,
        "account_code": t.account.code if t.account else None,
        "status": t.status,
        "subject": t.subject,
        "description": t.description,
        "severity": t.severity,
        "channel": t.channel,
        "assigned_to": t.assigned_to,
        "created_at": _iso(t.business_created_at),
        "last_customer_message_at": _iso(t.last_customer_message_at),
        "historical_resolution": t.historical_resolution,
    }


def agreement_to_dict(a: Agreement) -> dict:
    return {
        "code": a.code,
        "account_code": a.account.code if a.account else None,
        "title": a.title,
        "status": a.status,
        "effective_date": _iso(a.effective_date),
        "expiry_date": _iso(a.expiry_date),
        "source_file": a.source_file,
        "terms": a.terms,
        "body": a.body,
    }


def escalation_to_dict(e: Escalation) -> dict:
    return {
        "code": e.code,
        "account_id": e.account_id,
        "ticket_id": e.ticket_id,
        "severity": e.severity,
        "reason": e.reason,
        "assigned_to": e.assigned_to,
        "status": e.status,
        "created_at": _iso(e.created_at),
    }


def task_to_dict(t: FollowUpTask) -> dict:
    return {
        "code": t.code,
        "account_id": t.account_id,
        "ticket_id": t.ticket_id,
        "title": t.title,
        "description": t.description,
        "due_at": _iso(t.due_at),
        "status": t.status,
        "created_at": _iso(t.created_at),
    }
