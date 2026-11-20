"""What every MCP tool registrar is given: ToolContext (the bus, the expense views and the expenses recorder).

Part of the mcp adapter. server.create_server builds one and hands it to each registrar in TOOL_REGISTRARS, so adding
a dependency means adding a field here, not changing every registrar's signature.
"""

from dataclasses import dataclass

from app.core.cqrs import MessageBus
from app.modules import expenses
from app.modules.mcp.views import ExpenseViews


@dataclass(frozen=True)
class ToolContext:
    """The bus (commands and queries), the views (an expense as tools show it, category names to ids) and the
    recorder, which saves expenses (converting an amount in another currency to INR first, D204)."""

    bus: MessageBus
    views: ExpenseViews
    recorder: expenses.ExpenseRecorder
