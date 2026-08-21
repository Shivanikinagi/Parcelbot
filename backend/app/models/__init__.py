"""ORM models.

Importing this package registers every model on the shared declarative
``Base.metadata`` so string-based relationships resolve and
``Base.metadata.create_all`` sees all tables.
"""

from app.models.audit import AuditLog, ToolExecution
from app.models.conversation import Conversation, Message
from app.models.knowledge import Document, DocumentChunk
from app.models.logistics import Agreement, Order, Ticket
from app.models.organization import Account, User, agent_account_assignments
from app.models.workflow import Escalation, FollowUpTask

__all__ = [
    "Account",
    "User",
    "agent_account_assignments",
    "Order",
    "Ticket",
    "Agreement",
    "Conversation",
    "Message",
    "Escalation",
    "FollowUpTask",
    "AuditLog",
    "ToolExecution",
    "Document",
    "DocumentChunk",
]
