"""Deterministic seed: loads the real assessment dataset into the database.

Pipeline:
    1. Reset schema (drop + create).
    2. Read accounts / orders / tickets from the assessment workbook.
    3. Build agreements with machine-readable terms + human-readable bodies.
    4. Classify each ticket's severity (not present in the source data).
    5. Build the knowledge base: policy/SOP/guide/agreement docs + historical
       tickets, chunked and embedded (offline embedder by default).
    6. Create demo users spanning all four RBAC roles, with support assignments
       chosen to demonstrate account-scope boundaries.
    7. Compute per-account health scores for the ops dashboard.

Run:  python -m app.db.seed
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import openpyxl

from app.ai.embeddings import get_embedder
from app.core.clock import IST, ensure_ist
from app.core.config import BACKEND_ROOT
from app.core.constants import SOURCE_AUTHORITY, SourceType
from app.core.logging import configure_logging, get_logger
from app.db.base import Base, SessionLocal, engine
from app.db.knowledge_content import KNOWLEDGE_DOCUMENTS
from app.db.policy_data import AGREEMENT_TERMS
from app.models.knowledge import Document, DocumentChunk
from app.models.logistics import Agreement, Order, Ticket
from app.models.organization import Account, User
from app.services.severity_service import classify_severity

logger = get_logger(__name__)

WORKBOOK = BACKEND_ROOT / "knowledge" / "source_pack" / "ParcelPilot_Assessment_Data.xlsx"

# Agreement term windows (from the PDFs) keyed by account code.
_AGREEMENT_META = {
    "ACCT-001": {
        "kb_code": "AGR-NORTHSTAR",
        "effective": "2026-01-01",
        "expiry": "2026-12-31",
    },
    "ACCT-002": {
        "kb_code": "AGR-LUMENWORKS",
        "effective": "2026-03-01",
        "expiry": "2027-02-28",
    },
}

# Demo users: (name, email, role, account_code|None, assigned_codes)
_USERS = [
    ("Anjali Nair", "anjali@northstar.example", "customer", "ACCT-001", []),
    ("Ravi Menon", "ravi@lumenworks.example", "customer", "ACCT-002", []),
    ("Sunita Desai", "sunita@beacon.example", "customer", "ACCT-003", []),
    ("Vikram Shah", "vikram@axislabs.example", "customer", "ACCT-004", []),
    ("Rohit Sharma", "rohit@parcelpilot.com", "support", None, ["ACCT-001", "ACCT-004"]),
    ("Maya Iyer", "maya@parcelpilot.com", "support", None, ["ACCT-001", "ACCT-002"]),
    ("Priya Mehta", "priya@parcelpilot.com", "manager", None, []),
    ("Ops Admin", "admin@parcelpilot.com", "admin", None, []),
    ("Subrato Biswas", "subrato.biswas@trinamix.com", "admin", None, []),
]


def _parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=IST) if value.tzinfo is None else value.astimezone(IST)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _rows(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h).strip() for h in rows[0]]
    return [dict(zip(headers, r)) for r in rows[1:] if any(c is not None for c in r)]


def seed() -> None:
    configure_logging()
    logger.info("Resetting schema…")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    accounts_rows = _rows(wb["accounts"])
    orders_rows = _rows(wb["orders"])
    tickets_rows = _rows(wb["tickets"])

    session = SessionLocal()
    try:
        code_to_account: dict[str, Account] = {}

        # --- accounts ----------------------------------------------------
        for row in accounts_rows:
            acct = Account(
                code=row["account_id"],
                name=row["account_name"],
                plan=str(row["plan"]).lower(),
                status=str(row["status"]).lower(),
                csm=row.get("csm") or "",
                contract_file=row.get("contract_file"),
                premium_support=bool(row.get("premium_support")),
                notes=row.get("notes") or "",
            )
            session.add(acct)
            code_to_account[acct.code] = acct
        session.flush()

        # --- agreements --------------------------------------------------
        kb_by_code = {d["code"]: d for d in KNOWLEDGE_DOCUMENTS}
        for acct_code, meta in _AGREEMENT_META.items():
            acct = code_to_account.get(acct_code)
            if not acct:
                continue
            kb = kb_by_code[meta["kb_code"]]
            body = "\n\n".join(f"{s['heading']}\n{s['content']}" for s in kb["sections"])
            session.add(
                Agreement(
                    code=meta["kb_code"],
                    account_id=acct.id,
                    title=kb["title"],
                    version=kb["version"],
                    status="current",
                    effective_date=_parse_dt(meta["effective"]),
                    expiry_date=_parse_dt(meta["expiry"]),
                    source_file=kb["source_file"],
                    body=body,
                    terms=AGREEMENT_TERMS.get(acct_code, {}),
                )
            )
        session.flush()

        # --- orders ------------------------------------------------------
        for row in orders_rows:
            acct = code_to_account[row["account_id"]]
            session.add(
                Order(
                    code=row["order_id"],
                    account_id=acct.id,
                    carrier=row["carrier"],
                    status=str(row["status"]).upper(),
                    booked_at=_parse_dt(row.get("booked_at")),
                    pickup_window_start=_parse_dt(row.get("pickup_window_start")),
                    pickup_window_end=_parse_dt(row.get("pickup_window_end")),
                    pickup_actual_at=_parse_dt(row.get("pickup_actual_at")),
                    shipment_fee_inr=float(row.get("shipment_fee_inr") or 0),
                    carrier_fault=bool(row.get("carrier_fault")),
                    customer_fault=bool(row.get("customer_fault")),
                    cancellation_requested_at=_parse_dt(row.get("cancellation_requested_at")),
                    notes=row.get("notes") or "",
                )
            )
        session.flush()

        # --- tickets (with severity classification) ----------------------
        for row in tickets_rows:
            acct = code_to_account[row["account_id"]]
            sev = classify_severity(row["subject"], row.get("description") or "")
            session.add(
                Ticket(
                    code=row["ticket_id"],
                    account_id=acct.id,
                    business_created_at=_parse_dt(row.get("created_at")),
                    status=str(row["status"]).lower(),
                    subject=row["subject"],
                    description=row.get("description") or "",
                    channel=str(row.get("channel") or "email").lower(),
                    assigned_to=row.get("assigned_to"),
                    last_customer_message_at=_parse_dt(row.get("last_customer_message_at")),
                    historical_resolution=row.get("historical_resolution"),
                    severity=sev.severity,
                )
            )
        session.flush()

        # --- users -------------------------------------------------------
        for name, email, role, acct_code, assigned in _USERS:
            user = User(
                name=name,
                email=email.lower(),
                role=role,
                account_id=code_to_account[acct_code].id if acct_code else None,
            )
            user.assigned_accounts = [code_to_account[c] for c in assigned]
            session.add(user)
        session.flush()

        # --- knowledge base ---------------------------------------------
        _build_knowledge_base(session, code_to_account)

        # --- health scores ----------------------------------------------
        _compute_health(session, code_to_account)

        session.commit()
        logger.info(
            "Seed complete: %d accounts, %d orders, %d tickets, %d users, %d KB chunks.",
            len(accounts_rows),
            len(orders_rows),
            len(tickets_rows),
            len(_USERS),
            session.query(DocumentChunk).count(),
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _build_knowledge_base(session, code_to_account: dict[str, Account]) -> None:
    embedder = get_embedder()

    # 1. Curated documents (policies, SOP, guide, agreements).
    for doc in KNOWLEDGE_DOCUMENTS:
        source_type = doc["source_type"]
        st_value = source_type.value if isinstance(source_type, SourceType) else str(source_type)
        account_id = code_to_account[doc["account_code"]].id if doc.get("account_code") else None
        effective = _parse_dt(doc.get("effective_date"))
        document = Document(
            code=doc["code"],
            title=doc["title"],
            source_type=st_value,
            status=doc["status"],
            version=doc["version"],
            effective_date=effective,
            account_id=account_id,
            internal_only=bool(doc.get("internal_only")),
            source_file=doc.get("source_file"),
            meta={"source_file": doc.get("source_file")},
        )
        session.add(document)
        session.flush()

        contents = [s["content"] for s in doc["sections"]]
        vectors = embedder.embed_batch(contents)
        authority = SOURCE_AUTHORITY.get(SourceType(st_value), 5)
        for i, section in enumerate(doc["sections"]):
            session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=i,
                    heading=section["heading"],
                    content=section["content"],
                    token_estimate=len(section["content"].split()),
                    source_type=st_value,
                    status=doc["status"],
                    authority_rank=authority,
                    account_id=account_id,
                    internal_only=bool(doc.get("internal_only")),
                    effective_date=effective,
                    embedding=vectors[i],
                    meta={
                        "document_code": doc["code"],
                        "title": doc["title"],
                        "source_file": doc.get("source_file"),
                    },
                )
            )

    # 2. Historical (closed) tickets → low-authority, internal-only context.
    hist_authority = SOURCE_AUTHORITY[SourceType.HISTORICAL_TICKET]
    for ticket in session.query(Ticket).filter(Ticket.status == "closed").all():
        content = (
            f"Historical ticket {ticket.code} (CLOSED — context only, may be incorrect).\n"
            f"Subject: {ticket.subject}\n"
            f"Description: {ticket.description}\n"
            f"Recorded resolution: {ticket.historical_resolution or 'n/a'}"
        )
        document = Document(
            code=f"HIST-{ticket.code}",
            title=f"Historical ticket {ticket.code}",
            source_type=SourceType.HISTORICAL_TICKET.value,
            status="current",
            version="1",
            account_id=ticket.account_id,
            internal_only=True,
            meta={"ticket_code": ticket.code},
        )
        session.add(document)
        session.flush()
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                heading=f"{ticket.code} — {ticket.subject}",
                content=content,
                token_estimate=len(content.split()),
                source_type=SourceType.HISTORICAL_TICKET.value,
                status="current",
                authority_rank=hist_authority,
                account_id=ticket.account_id,
                internal_only=True,
                embedding=embedder.embed(content),
                meta={
                    "document_code": f"HIST-{ticket.code}",
                    "title": f"Historical ticket {ticket.code}",
                    "source_file": None,
                },
            )
        )


def _compute_health(session, code_to_account: dict[str, Account]) -> None:
    """Simple composite health score: penalise open, high-severity tickets."""
    from app.repositories.logistics_repo import AgreementRepository
    from app.services.sla_service import compute_sla

    # A manager principal to run SLA computations unrestricted during seeding.
    from app.core.security import Principal, Role

    seed_principal = Principal(user_id=0, email="seed@system", name="seed", role=Role.ADMIN)
    agr_repo = AgreementRepository(session, seed_principal)

    penalty = {"P1": 25, "P2": 10, "P3": 3}
    for acct in code_to_account.values():
        score = 100.0
        open_tickets = (
            session.query(Ticket)
            .filter(Ticket.account_id == acct.id, Ticket.status == "open")
            .all()
        )
        for t in open_tickets:
            sev = t.severity or "P3"
            score -= penalty.get(sev, 3)
            if t.business_created_at:
                agreement = agr_repo.get_current_for_account(acct.id)
                sla = compute_sla(acct, agreement, sev, t.business_created_at)
                if sla.breached:
                    score -= 10
        acct.health_score = max(0.0, min(100.0, round(score, 1)))


if __name__ == "__main__":
    seed()
