"""The delete_expense MCP tool: delete one expense for good, only with confirmed=true.

Part of the mcp adapter. register_delete_expense adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it sends the expenses module's DeleteExpense through the bus
(with expected_version, the version check is in the DELETE itself), then answers with what was deleted
(ExpenseDeleted). The assistant's web panel never lets the model call it: only the user's Approve does.

What clients see comes from the tool function: the SDK builds the input schema (titled
"delete_expenseArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.cqrs import MessageBus
from app.core.errors import BusinessRuleError
from app.modules import expenses
from app.modules.mcp.contracts import (
    CONFIRM_ARGUMENT,
    EXPECTED_VERSION_ARGUMENT,
    EXPENSE_ID_ARGUMENT,
    ExpenseDeleted,
    ToolName,
)
from app.modules.mcp.tools.support import CHANGES_DATA, ExpenseIdArg, require_arguments, tool_errors
from app.modules.mcp.views import ExpenseViews


def register_delete_expense(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the delete_expense tool: delete one expense (DeleteExpense) and answer with what was deleted.

    Raises RuntimeError at start-up if the tool lacks an argument the contract names (expense_id,
    confirmed, expected_version).
    """

    # Deletes for good, only with confirmed=true. With expected_version, the expenses module deletes in
    # one statement (DELETE ... WHERE id = ? AND version = ?), so an edit made since the user saw the
    # expense stops the delete instead of being lost.
    @server.tool(
        name=ToolName.DELETE_EXPENSE,
        annotations=CHANGES_DATA,
        description=f"Delete an expense permanently. Show it to the user first ({ToolName.GET_EXPENSE}), and call "
        f"this only after they have clearly agreed, with {CONFIRM_ARGUMENT}=true. Pass the {EXPECTED_VERSION_ARGUMENT} "
        "you showed them, so a change made since then stops the delete.",
    )
    def delete_expense(
        expense_id: ExpenseIdArg,
        # A required interlock, not a preview switch (previews are get_expense). The SDK ignores
        # arguments a tool doesn't declare, so without this a client still sending the old
        # confirmed=false ("just show me") would delete for real. strict: only a real true, not "yes" or 1.
        confirmed: Annotated[bool, Field(strict=True, description="Must be true: the user has clearly agreed.")],
        expected_version: Annotated[
            int | None, Field(ge=1, description="Delete only if the expense is still at this version.")
        ] = None,
    ) -> ExpenseDeleted:
        with tool_errors():
            if confirmed is not True:
                raise BusinessRuleError(
                    f"Nothing was deleted: {CONFIRM_ARGUMENT} must be true, after the user has agreed."
                )
            # Read before deleting: the answer shows what was deleted, and a missing expense is a clear
            # "not found" before anything changes.
            expense = views.find(expense_id)
            bus.execute(expenses.DeleteExpense(expense_id=expense_id, expected_version=expected_version))
            return ExpenseDeleted(deleted=expense)

    require_arguments(delete_expense, EXPENSE_ID_ARGUMENT, CONFIRM_ARGUMENT, EXPECTED_VERSION_ARGUMENT)
