"""Knowledge base: list visible documents and run a direct search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.core.security import Principal
from app.tools.base import ToolContext

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.repositories.knowledge_repo import KnowledgeRepository

    docs = KnowledgeRepository(db, principal).list_documents()
    return [
        {
            "code": d.code, "title": d.title, "source_type": d.source_type,
            "status": d.status, "version": d.version, "internal_only": d.internal_only,
            "authority_rank": None, "source_file": d.source_file,
            "effective_date": d.effective_date.isoformat() if d.effective_date else None,
        }
        for d in docs
    ]


@router.get("/search")
def search(q: str = Query(..., min_length=2), db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    from app.tools import registry

    ctx = ToolContext(db, principal)
    result = registry.get_tool("document_search").execute(ctx, {"query": q})
    return {
        "summary": result.summary,
        "passages": result.data.get("passages", []),
        "confidence": result.data.get("confidence", 0.0),
        "conflicts": [c.model_dump() for c in result.conflicts],
        "citations": [c.model_dump() for c in result.citations],
    }
