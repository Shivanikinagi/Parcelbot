"""Catalog router: RBAC-scoped read access to orders, tickets, accounts, agreements.

Every endpoint resolves data through principal-scoped repositories, so a
customer only ever sees their own account's records. Ticket detail enriches the
row with live severity classification, SLA status, and known-issue matches.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.core.exceptions import NotFoundError
from app.core.security import Principal
from app.schemas.serialize import (
    account_to_dict,
    agreement_to_dict,
    order_to_dict,
    ticket_to_dict,
)
from app.services.known_issues import match_known_issues
from app.services.severity_service import classify_severity
from app.services.sla_service import compute_sla

router = APIRouter(tags=["catalog"])


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.organization_repo import AccountRepository

    return [account_to_dict(a) for a in AccountRepository(db, principal).list_accounts()]


@router.get("/orders")
def list_orders(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.logistics_repo import OrderRepository

    return [order_to_dict(o) for o in OrderRepository(db, principal).list_all()]


@router.get("/orders/{code}")
def get_order(code: str, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.logistics_repo import OrderRepository

    order = OrderRepository(db, principal).get_by_code(code)
    if order is None:
        raise NotFoundError("Order not found or not in your scope.")
    return order_to_dict(order)


@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.logistics_repo import AgreementRepository, TicketRepository

    tickets = TicketRepository(db, principal).list_all()
    agr_repo = AgreementRepository(db, principal)
    out = []
    for t in tickets:
        row = ticket_to_dict(t)
        if t.status == "open" and t.business_created_at:
            from app.repositories.organization_repo import AccountRepository

            account = AccountRepository(db, principal).get_by_id(t.account_id)
            agreement = agr_repo.get_current_for_account(t.account_id)
            sla = compute_sla(account, agreement, t.severity or "P3", t.business_created_at)
            row["sla"] = {"target_human": sla.target_human, "breached": sla.breached,
                          "remaining_minutes": sla.remaining_minutes, "source": sla.source}
        out.append(row)
    return out


@router.get("/tickets/{code}")
def get_ticket(code: str, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.logistics_repo import AgreementRepository, TicketRepository
    from app.repositories.organization_repo import AccountRepository

    ticket = TicketRepository(db, principal).get_by_code(code)
    if ticket is None:
        raise NotFoundError("Ticket not found or not in your scope.")
    account = AccountRepository(db, principal).get_by_id(ticket.account_id)
    agreement = AgreementRepository(db, principal).get_current_for_account(ticket.account_id)
    sev = classify_severity(ticket.subject, ticket.description)
    row = ticket_to_dict(ticket)
    row["classified_severity"] = sev.model_dump()
    row["known_issues"] = match_known_issues(f"{ticket.subject} {ticket.description}", account.plan if account else None)
    if ticket.business_created_at:
        sla = compute_sla(account, agreement, sev.severity, ticket.business_created_at)
        row["sla"] = sla.model_dump(mode="json")
    return row


@router.get("/agreements/{account_code}")
def get_agreement(account_code: str, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.logistics_repo import AgreementRepository
    from app.repositories.organization_repo import AccountRepository

    account = AccountRepository(db, principal).get_by_code(account_code)
    if account is None:
        raise NotFoundError("Account not found or not in your scope.")
    agreement = AgreementRepository(db, principal).get_current_for_account(account.id)
    return {
        "account": account_to_dict(account),
        "agreement": agreement_to_dict(agreement) if agreement else None,
    }
