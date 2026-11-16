"""The MCP resources: read-only data a client can load as context (the categories, the recent expenses).

Part of the mcp adapter; server.py calls register_resources once, after the tools. The SDK names each
resource after its function and describes it with the function's docstring, so those stay exactly as they
are.
"""

import json

from mcp.server.mcpserver import MCPServer

from app.core.cqrs import MessageBus
from app.modules import categories, expenses
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ResourceUri
from app.modules.mcp.views import ExpenseViews, to_view

# How many expenses the "recent" resource holds: each one costs the client's model tokens.
RECENT_ROWS = 20
# Both resources are JSON text.
JSON_MIME_TYPE = "application/json"


def register_resources(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the categories and recent-expenses resources to the server.

    Each read sends queries through the bus. The recent list names its categories with one ListCategories,
    not one query per row.
    """

    # The categories as the categories module returns them, so a model can use their exact names. They're shared by
    # everyone (no caller needed).
    @server.resource(ResourceUri.CATEGORIES, mime_type=JSON_MIME_TYPE)
    def categories_resource() -> str:
        """The expense categories that exist (id, name, icon)."""
        return json.dumps([c.model_dump() for c in bus.ask(categories.ListCategories())])

    # The caller's newest RECENT_ROWS expenses, shown like the tools show them (ExpenseView). Without a caller (or
    # with a token that stopped working) the read fails: nobody's expenses are shown (caller.py, D191).
    @server.resource(ResourceUri.RECENT, mime_type=JSON_MIME_TYPE)
    def recent_expenses_resource() -> str:
        """The most recent expenses, newest first."""
        newest = expenses.ExpenseFilters(limit=RECENT_ROWS)
        rows = bus.ask(expenses.ListExpenses(owner_id=current_caller(), filters=newest)).items
        names = views.category_names()
        return json.dumps([to_view(e, names).model_dump(mode="json") for e in rows])
