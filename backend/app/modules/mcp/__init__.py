"""MCP module: exposes SpendWise's expense tools and resources over the Model Context Protocol.

It owns no tables and no business rules. Like a REST router, it is only an adapter: it turns MCP
calls into commands and queries for the expenses and categories modules.

Inside: contracts.py (names and typed results), server.py (assembles the server), read_tools.py and
write_tools.py (the tools), resources.py, views.py (expenses as the tools show them), tool_support.py
(what the tools share), http.py (the HTTP endpoint and its bearer token), module.py (for bootstrap).

Public interface, for other modules (the assistant): the contract below (tool and argument names,
resource addresses, the typed results). Importing it loads no server code. The composition root
builds the server through module.py.
"""

from app.modules.mcp.contracts import (
    AUTHORIZATION_HEADER,
    BEARER_SCHEME,
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
    "AUTHORIZATION_HEADER",
    "BEARER_SCHEME",
    "CLEAR_NOTE_ARGUMENT",
    "CONFIRM_ARGUMENT",
    "EXPECTED_VERSION_ARGUMENT",
    "EXPENSE_ID_ARGUMENT",
    "SERVER_NAME",
    "ExpenseDeleted",
    "ExpenseFound",
    "ExpenseSaved",
    "ExpenseSearch",
    "ExpenseUpdated",
    "ExpenseView",
    "MonthSpending",
    "ResourceUri",
    "ToolName",
]
