"""Conversations & messages. A user sees their own threads; managers see all."""

from __future__ import annotations

from sqlalchemy import select

from app.core.exceptions import AccessDeniedError, NotFoundError
from app.models.conversation import Conversation, Message
from app.repositories.base import ScopedRepository


class ConversationRepository(ScopedRepository):
    def create(self, title: str = "New conversation") -> Conversation:
        convo = Conversation(
            user_id=self.principal.user_id,
            account_id=self.principal.account_id,
            title=title[:240],
        )
        self.session.add(convo)
        self.session.flush()
        return convo

    def get(self, conversation_id: int) -> Conversation:
        convo = self.session.get(Conversation, conversation_id)
        if convo is None:
            raise NotFoundError("Conversation not found.")
        if convo.user_id != self.principal.user_id and not self.principal.role.is_privileged:
            raise AccessDeniedError("You cannot access this conversation.")
        return convo

    def list_for_user(self, limit: int = 100) -> list[Conversation]:
        stmt = select(Conversation)
        if not self.principal.role.is_privileged:
            stmt = stmt.where(Conversation.user_id == self.principal.user_id)
        stmt = stmt.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def add_message(
        self, conversation_id: int, role: str, content: str, meta: dict | None = None
    ) -> Message:
        self.get(conversation_id)  # authorization check
        msg = Message(conversation_id=conversation_id, role=role, content=content, meta=meta or {})
        self.session.add(msg)
        self.session.flush()
        return msg

    def messages(self, conversation_id: int) -> list[Message]:
        self.get(conversation_id)  # authorization check
        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        return list(self.session.scalars(stmt))

    def set_title(self, conversation_id: int, title: str) -> Conversation:
        convo = self.get(conversation_id)
        convo.title = title[:240]
        self.session.flush()
        return convo

    def set_pinned(self, conversation_id: int, pinned: bool) -> Conversation:
        convo = self.get(conversation_id)
        convo.pinned = pinned
        self.session.flush()
        return convo
