"""Knowledge-base documents and their embedded chunks.

Each :class:`DocumentChunk` carries denormalised ranking metadata
(``source_type``, ``authority_rank``, freshness) so the retriever can score a
candidate without extra joins. Embeddings are stored as JSON float arrays for
the local SQLite profile; in the Postgres profile this column becomes a native
``pgvector`` column (the vector store abstracts the difference).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """A source document in the knowledge base (policy, SOP, agreement, …)."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("code", name="uq_documents_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    #: One of app.core.constants.SourceType values.
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    #: "current" | "deprecated"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Account scope — non-null only for account-specific docs (agreements).
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    #: True → only internal staff (support+) may retrieve/cite this document.
    internal_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(200))
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index"
    )


class DocumentChunk(Base, TimestampMixin):
    """A retrievable slice of a document with its embedding and ranking metadata."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Denormalised for fast ranking (avoids a join per candidate).
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    authority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    account_id: Mapped[int | None] = mapped_column(Integer, index=True)
    internal_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: JSON float array (local) / pgvector (prod). May be null before indexing.
    embedding: Mapped[list | None] = mapped_column(JSON)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    document: Mapped["Document"] = relationship(back_populates="chunks")
