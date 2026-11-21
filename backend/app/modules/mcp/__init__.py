"""MCP module: exposes SpendWise's expense tools and resources over the Model Context Protocol.

It owns no tables and no business rules. Like a REST router, it is only an adapter: it turns MCP
calls into commands and queries for the expenses and categories modules.

Inside: contracts.py (names and typed results), server.py (assembles the server), tools/ (the tools, one
file each, and support.py: what they share), resources.py, views.py (expenses as the tools show them),
caller.py (who a request acts for), http.py (the HTTP endpoint and its access-token check), module.py (for
bootstrap). Every tool acts for one person, its caller, and touches only their expenses (D191).

Public interface, for other modules (the assistant) and the stdio server: the contract below (tool and argument
names, resource addresses, the typed results) and how to set the caller (acting_for, act_for_process). Importing it
loads no server code. The composition root builds the server through module.py.
"""

from app.modules.mcp.caller import CallerLookup, act_for_process, acting_for
from app.modules.mcp.contracts import (
    CLEAR_NOTE_ARGUMENT,
    CONFIRM_ARGUMENT,
    EXPECTED_VERSION_ARGUMENT,
    EXPENSE_ID_ARGUMENT,
    SERVER_NAME,
    ExpenseDeleted,
    ExpenseFound,
    ExpenseSaved,
    ExpenseSearch,
    ExpenseUpdated,
    ExpenseView,
    MonthSpending,
    ResourceUri,
    ToolName,
)

__all__ = [
    "CLEAR_NOTE_ARGUMENT",
    "CONFIRM_ARGUMENT",
    "EXPECTED_VERSION_ARGUMENT",
    "EXPENSE_ID_ARGUMENT",
    "SERVER_NAME",
    "CallerLookup",
    "ExpenseDeleted",
    "ExpenseFound",
    "ExpenseSaved",
    "ExpenseSearch",
    "ExpenseUpdated",
    "ExpenseView",
    "MonthSpending",
    "ResourceUri",
    "ToolName",
    "act_for_process",
    "acting_for",
]
