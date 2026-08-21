"""Chat router: SSE streaming agent responses + action confirmation.

A single endpoint handles both a normal message and confirmation of a
previously-prepared action (``confirm_action`` in the body).

Session lifecycle note: the response body is a generator that runs *after*
FastAPI would tear down a request-scoped dependency session. So the generator
owns its own session for the whole turn — create conversation, persist the user
turn, run the agent, stream, persist the assistant turn, and commit — which is
the correct pattern for SSE + a database.

Event order: ``start`` → ``meta`` (citations, conflicts, reasoning trace, tool
timeline, confidence, pending action) → ``token``* (streamed prose) → ``done``.
The UI renders the side panels from ``meta`` while the prose types in.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.graph import run_agent
from app.agent.narrator import stream_narration
from app.agent.state import AgentState
from app.api.deps import enforce_rate_limit
from app.core.exceptions import ParcelPilotError
from app.core.logging import get_logger, request_id_ctx
from app.db.base import SessionLocal
from app.repositories.conversation_repo import ConversationRepository
from app.schemas.api import ChatRequest
from app.core.security import Principal
from app.tools.base import ToolContext

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


def _build_meta(state: AgentState) -> dict:
    answer = state.get("answer", {})
    return {
        "intent": state.get("intent", {}).get("type"),
        "summary": answer.get("summary", ""),
        "recommendation": answer.get("recommendation", ""),
        "confidence": answer.get("confidence", 0.0),
        "confidence_band": answer.get("confidence_band", "LOW"),
        "citations": state.get("citations", []),
        "conflicts": state.get("conflicts", []),
        "trace": state.get("trace", []),
        "tool_calls": state.get("tool_calls", []),
        "evidence": state.get("evidence", []),
        "pending_action": state.get("pending_action"),
        "escalation": state.get("escalation"),
        "committed": state.get("committed"),
    }


@router.post("/message")
def chat_message(body: ChatRequest, principal: Principal = Depends(enforce_rate_limit)):
    request_id = request_id_ctx.get()

    def generate() -> Iterator[str]:
        db = SessionLocal()
        try:
            conv_repo = ConversationRepository(db, principal)
            if body.conversation_id:
                conversation = conv_repo.get(body.conversation_id)
            else:
                conversation = conv_repo.create(title=body.message[:60] or "New conversation")
            conv_id = conversation.id
            ctx = ToolContext(db, principal, request_id=request_id, conversation_id=conv_id)

            conv_repo.add_message(conv_id, "user", body.message)
            yield _sse({"type": "start", "conversation_id": conv_id})

            state = run_agent(ctx, body.message, body.confirm_action)
            meta = _build_meta(state)
            yield _sse({"type": "meta", "conversation_id": conv_id, "meta": meta})

            collected: list[str] = []
            for chunk in stream_narration(state):
                collected.append(chunk)
                yield _sse({"type": "token", "content": chunk})

            text = "".join(collected).strip() or meta.get("summary", "")
            message = conv_repo.add_message(conv_id, "assistant", text, meta=meta)
            db.commit()
            yield _sse({"type": "done", "message_id": message.id, "conversation_id": conv_id})
        except ParcelPilotError as exc:
            db.rollback()
            yield _sse({"type": "error", "message": exc.message, "code": exc.code})
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("Chat turn failed")
            yield _sse({"type": "error", "message": "The assistant hit an unexpected error."})
        finally:
            db.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
