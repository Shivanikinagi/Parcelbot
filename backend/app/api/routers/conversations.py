"""Conversation history: list, read, create, rename, pin."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.core.security import Principal
from app.repositories.conversation_repo import ConversationRepository
from app.schemas.api import ConversationOut, MessageOut, PinUpdate, TitleUpdate

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _conv_out(c) -> ConversationOut:
    return ConversationOut(id=c.id, title=c.title, pinned=c.pinned, updated_at=c.updated_at.isoformat())


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    repo = ConversationRepository(db, principal)
    return [_conv_out(c) for c in repo.list_for_user()]


@router.post("", response_model=ConversationOut)
def create_conversation(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    repo = ConversationRepository(db, principal)
    conv = repo.create()
    db.commit()
    return _conv_out(conv)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: int, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    repo = ConversationRepository(db, principal)
    return [
        MessageOut(id=m.id, role=m.role, content=m.content, meta=m.meta, created_at=m.created_at.isoformat())
        for m in repo.messages(conversation_id)
    ]


@router.patch("/{conversation_id}/title", response_model=ConversationOut)
def rename(conversation_id: int, body: TitleUpdate, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    repo = ConversationRepository(db, principal)
    conv = repo.set_title(conversation_id, body.title)
    db.commit()
    return _conv_out(conv)


@router.patch("/{conversation_id}/pin", response_model=ConversationOut)
def pin(conversation_id: int, body: PinUpdate, db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    repo = ConversationRepository(db, principal)
    conv = repo.set_pinned(conversation_id, body.pinned)
    db.commit()
    return _conv_out(conv)
