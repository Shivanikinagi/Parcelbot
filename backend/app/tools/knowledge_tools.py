"""Knowledge tools: document search (RAG) and known-issue matching."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.config import settings
from app.retrieval.retriever import HybridRetriever, build_context_block
from app.schemas.results import Citation
from app.services.conflict_service import detect_source_conflicts
from app.services.known_issues import match_known_issues
from app.tools.base import Tool, ToolContext, ToolResult


class DocumentSearchArgs(BaseModel):
    query: str = Field(..., min_length=2, description="Natural-language search query.")
    top_k: int = Field(default=settings.retrieval_top_k, ge=1, le=12)
    context_account_id: int | None = Field(
        default=None,
        description="Account this query is actually about (from a ticket/order/account entity or the caller's own account), if any. Scopes agreement-authority boosting so an unrelated customer's contract can't outrank general policy.",
    )


class DocumentSearchTool(Tool):
    name = "document_search"
    description = (
        "Search the knowledge base (policies, SOPs, product guide, and the caller's "
        "in-scope customer agreements) for relevant clauses. Returns ranked, cited "
        "evidence with authority/freshness scores and flags any source conflicts."
    )
    input_model = DocumentSearchArgs
    required_permission = "chat"

    def run(self, ctx: ToolContext, args: DocumentSearchArgs) -> ToolResult:
        chunks = ctx.knowledge().list_visible_chunks()
        hits, confidence = HybridRetriever(chunks).retrieve(
            args.query, top_k=args.top_k, context_account_id=args.context_account_id
        )
        conflicts = detect_source_conflicts(hits)
        citations = [Citation(**hit.citation(i + 1)) for i, hit in enumerate(hits)]
        summary = (
            f"Retrieved {len(hits)} passage(s) (confidence {confidence:.2f})."
            if hits
            else "No relevant passages found in the knowledge base."
        )
        return ToolResult(
            tool=self.name,
            ok=True,
            summary=summary,
            citations=citations,
            conflicts=conflicts,
            data={
                "confidence": confidence,
                "context_block": build_context_block(hits),
                "passages": [
                    {
                        "marker": f"S{i + 1}",
                        "title": h.title,
                        "heading": h.heading,
                        "content": h.content,
                        "source_type": h.source_type,
                        "status": h.status,
                        "scores": h.scores,
                    }
                    for i, h in enumerate(hits)
                ],
            },
        )


class KnownIssueArgs(BaseModel):
    text: str = Field(..., min_length=2, description="Ticket/issue text to match against known issues.")
    plan: str | None = Field(default=None, description="Optional account plan to filter plan-specific issues.")


class KnownIssueMatchTool(Tool):
    name = "known_issue_match"
    description = (
        "Match a problem description against ParcelPilot's current known issues "
        "(KI-208 bulk-upload, KI-211 SwiftShip webhook delay, KI-176 resolved). Returns "
        "operational guidance and workarounds."
    )
    input_model = KnownIssueArgs
    required_permission = "chat"

    def run(self, ctx: ToolContext, args: KnownIssueArgs) -> ToolResult:
        matches = match_known_issues(args.text, args.plan)
        if not matches:
            return ToolResult(tool=self.name, ok=True, summary="No known issue matched.", data={"matches": []})
        summary = "Matched known issue(s): " + ", ".join(m["code"] for m in matches)
        return ToolResult(
            tool=self.name,
            ok=True,
            summary=summary,
            data={"matches": matches},
            citations=[
                Citation(
                    document_code="OPS-GUIDE-KI",
                    title="ParcelPilot Product Operations Guide & Known Issues",
                    heading=f"{m['code']} — {m['title']}",
                    source_type="operational_guide",
                    status="current",
                    authority_rank=4,
                    source_file="04_Product_Operations_Guide_and_Known_Issues.pdf",
                )
                for m in matches
            ],
        )
