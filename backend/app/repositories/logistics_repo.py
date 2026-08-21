"""RBAC-scoped repositories for orders, tickets, and agreements."""

from __future__ import annotations

from sqlalchemy import or_, select

from app.models.logistics import Agreement, Order, Ticket
from app.repositories.base import ScopedRepository


class OrderRepository(ScopedRepository):
    def get_by_code(self, code: str) -> Order | None:
        stmt = self.apply_account_scope(
            select(Order).where(Order.code == code.strip().upper()), Order.account_id
        )
        return self.session.scalar(stmt)

    def get_by_id(self, order_id: int) -> Order | None:
        stmt = self.apply_account_scope(select(Order).where(Order.id == order_id), Order.account_id)
        return self.session.scalar(stmt)

    def list_for_account(self, account_id: int) -> list[Order]:
        stmt = self.apply_account_scope(
            select(Order).where(Order.account_id == account_id).order_by(Order.code),
            Order.account_id,
        )
        return list(self.session.scalars(stmt))

    def list_all(self, limit: int = 200) -> list[Order]:
        stmt = self.apply_account_scope(select(Order).order_by(Order.code), Order.account_id)
        return list(self.session.scalars(stmt.limit(limit)))


class TicketRepository(ScopedRepository):
    def get_by_code(self, code: str) -> Ticket | None:
        stmt = self.apply_account_scope(
            select(Ticket).where(Ticket.code == code.strip().upper()), Ticket.account_id
        )
        return self.session.scalar(stmt)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        stmt = self.apply_account_scope(
            select(Ticket).where(Ticket.id == ticket_id), Ticket.account_id
        )
        return self.session.scalar(stmt)

    def list_for_account(self, account_id: int) -> list[Ticket]:
        stmt = self.apply_account_scope(
            select(Ticket).where(Ticket.account_id == account_id).order_by(Ticket.code),
            Ticket.account_id,
        )
        return list(self.session.scalars(stmt))

    def list_open(self, limit: int = 200) -> list[Ticket]:
        stmt = self.apply_account_scope(
            select(Ticket).where(Ticket.status == "open").order_by(Ticket.business_created_at),
            Ticket.account_id,
        )
        return list(self.session.scalars(stmt.limit(limit)))

    def list_all(self, limit: int = 200) -> list[Ticket]:
        stmt = self.apply_account_scope(select(Ticket).order_by(Ticket.code), Ticket.account_id)
        return list(self.session.scalars(stmt.limit(limit)))

    def search_history(self, query: str, limit: int = 20) -> list[Ticket]:
        """Keyword search over historical (closed) tickets — context only."""
        like = f"%{query.strip()}%"
        stmt = select(Ticket).where(
            Ticket.status == "closed",
            or_(
                Ticket.subject.ilike(like),
                Ticket.description.ilike(like),
                Ticket.historical_resolution.ilike(like),
            ),
        )
        stmt = self.apply_account_scope(stmt, Ticket.account_id).limit(limit)
        return list(self.session.scalars(stmt))


class AgreementRepository(ScopedRepository):
    """Agreements are the highest-authority source and are account-scoped."""

    def get_current_for_account(self, account_id: int) -> Agreement | None:
        stmt = self.apply_account_scope(
            select(Agreement)
            .where(Agreement.account_id == account_id, Agreement.status == "current")
            .order_by(Agreement.effective_date.desc()),
            Agreement.account_id,
        )
        return self.session.scalar(stmt)

    def list_for_account(self, account_id: int) -> list[Agreement]:
        stmt = self.apply_account_scope(
            select(Agreement).where(Agreement.account_id == account_id), Agreement.account_id
        )
        return list(self.session.scalars(stmt))
