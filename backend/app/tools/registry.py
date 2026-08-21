"""Central tool registry.

Holds one instance of each tool and exposes lookup + capability description. The
planner uses :func:`describe_tools` (filtered to the principal's permissions) to
decide which tools to call; the executor uses :func:`get_tool` to run them.
"""

from __future__ import annotations

from app.core.security import Principal
from app.tools.analytics_tools import AnalyticsTool
from app.tools.action_tools import (
    EscalationCreatorTool,
    FollowUpTaskCreatorTool,
    TicketUpdateTool,
)
from app.tools.base import Tool
from app.tools.data_tools import (
    AgreementLookupTool,
    AuditLogTool,
    CustomerHistoryTool,
    OrderLookupTool,
    StructuredDataQueryTool,
    TicketLookupTool,
)
from app.tools.knowledge_tools import DocumentSearchTool, KnownIssueMatchTool
from app.tools.reasoning_tools import (
    CancellationEvaluatorTool,
    SLACalculatorTool,
    ServiceCreditEvaluatorTool,
    ServiceCreditScenarioTool,
)

_ALL_TOOLS: list[Tool] = [
    DocumentSearchTool(),
    KnownIssueMatchTool(),
    OrderLookupTool(),
    TicketLookupTool(),
    AgreementLookupTool(),
    CustomerHistoryTool(),
    AuditLogTool(),
    StructuredDataQueryTool(),
    SLACalculatorTool(),
    CancellationEvaluatorTool(),
    ServiceCreditEvaluatorTool(),
    ServiceCreditScenarioTool(),
    EscalationCreatorTool(),
    FollowUpTaskCreatorTool(),
    TicketUpdateTool(),
    AnalyticsTool(),
]

TOOLS: dict[str, Tool] = {t.name: t for t in _ALL_TOOLS}


def register(tool: Tool) -> None:
    TOOLS[tool.name] = tool


def get_tool(name: str) -> Tool | None:
    return TOOLS.get(name)


def all_tools() -> list[Tool]:
    return list(TOOLS.values())


def _can_use(principal: Principal, tool: Tool) -> bool:
    if tool.required_permission and not principal.can(tool.required_permission):
        return False
    return True


def describe_tools(principal: Principal) -> list[dict]:
    """Machine-readable descriptions of tools this principal may call."""
    out = []
    for tool in TOOLS.values():
        if not _can_use(principal, tool):
            continue
        out.append(
            {
                "name": tool.name,
                "description": tool.description,
                "state_changing": tool.state_changing,
                "parameters": tool.input_model.model_json_schema(),
            }
        )
    return out
