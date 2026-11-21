"""The get_expense MCP tool: one expense by its id.

Part of the mcp adapter. register_get_expense adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it reads the expense through the bus (views.ExpenseViews.find)
and answers with a typed result (ExpenseFound) that names its category. It only reads.

What clients see comes from the tool function: the SDK builds the input schema (titled
"get_expenseArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from mcp.server.mcpserver import MCPServer

from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import EXPENSE_ID_ARGUMENT, ExpenseFound, ToolName
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.support import READS_ONLY, ExpenseIdArg, require_arguments, tool_errors


def register_get_expense(server: MCPServer, context: ToolContext) -> None:
    """Add the get_expense tool: one expense by id, or a "not found" tool error.

    Raises RuntimeError at start-up if the tool lacks the argument the contract names (expense_id).
    """
    views = context.views

    # The assistant calls it to show an expense (and its version) before a delete is approved.
    @server.tool(
        name=ToolName.GET_EXPENSE,
        annotations=READS_ONLY,
        description="Get one expense by its id, e.g. to show it to the user before changing or deleting it.",
    )
    def get_expense(expense_id: ExpenseIdArg) -> ExpenseFound:
        with tool_errors():
            # Another person's expense is "not found" (caller.py, D191).
            return ExpenseFound(expense=views.find(current_caller(), expense_id))

    require_arguments(get_expense, EXPENSE_ID_ARGUMENT)
