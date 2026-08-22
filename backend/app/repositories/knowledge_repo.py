"""RBAC-scoped access to knowledge-base documents and chunks (for retrieval).

Two independent filters are applied to every chunk read:
    1. **Account scope** — global chunks (``account_id is NULL``) are visible to
       all; account-specific chunks (agreements) only to principals who may see
       that account.
    2. **Audience** — ``internal_only`` chunks (ops guide, deprecated policy,
       historical tickets) are hidden from customers entirely.
Together these guarantee a customer can never retrieve or cite another
account's agreement, nor internal operational material.
"""

from __future__ import annotations

from sqlalchemy import or_, select

from app.models.knowledge import Document, DocumentChunk
from app.repositories.base import ScopedRepository


class KnowledgeRepository(ScopedRepository):
    def _visible_chunk_filter(self, stmt):
        allowed = self._scope_ids()
        if allowed is not None:
            ids = list(allowed) if allowed else [-1]
            stmt = stmt.where(
                or_(DocumentChunk.account_id.is_(None), DocumentChunk.account_id.in_(ids))
            )
        if not self.principal.role.is_internal:
            stmt = stmt.where(DocumentChunk.internal_only.is_(False))
        return stmt

    def list_visible_chunks(self) -> list[DocumentChunk]:
        """All chunks this principal may retrieve (corpus for hybrid search).

        The dataset is small enough to rank in-process; for production scale the
        vector similarity step would be pushed to pgvector with the same filters
        expressed as SQL predicates.
        """
        stmt = self._visible_chunk_filter(select(DocumentChunk))
        return list(self.session.scalars(stmt))

    def get_document(self, document_id: int) -> Document | None:
        return self.session.get(Document, document_id)

    def get_document_by_code(self, code: str) -> Document | None:
        """RBAC-checked lookup used to let a citation be opened and read in full."""
        doc = self.session.scalar(select(Document).where(Document.code == code))
        if doc is None or not self.can_access_account(doc.account_id):
            return None
        if doc.internal_only and not self.principal.role.is_internal:
            return None
        return doc

    def list_chunks_for_document(self, document_id: int) -> list[DocumentChunk]:
        stmt = self._visible_chunk_filter(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(self.session.scalars(stmt))

    def list_documents(self, include_internal: bool = True) -> list[Document]:
        stmt = select(Document).order_by(Document.source_type, Document.code)
        allowed = self._scope_ids()
        if allowed is not None:
            ids = list(allowed) if allowed else [-1]
            stmt = stmt.where(or_(Document.account_id.is_(None), Document.account_id.in_(ids)))
        if not (include_internal and self.principal.role.is_internal):
            stmt = stmt.where(Document.internal_only.is_(False))
        return list(self.session.scalars(stmt))
