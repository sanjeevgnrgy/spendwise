"""The update_expense MCP tool: change some fields of an expense, and answer with the result.

Part of the mcp adapter. register_update_expense adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it turns the fields given into the expenses module's
UpdateExpense, sent through the expenses module's recorder (which converts a new amount, currency or date in
another currency to INR first, D204), so MCP callers get exactly the REST API's rules (and the version is raised),
then answers with the expense after the change (ExpenseUpdated) and the budgets the change pushed near or over
their limit (budget_watch.py).

What clients see comes from the tool function: the SDK builds the input schema (titled
"update_expenseArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.errors import BusinessRuleError
from app.modules import expenses
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import CLEAR_NOTE_ARGUMENT, EXPENSE_ID_ARGUMENT, ExpenseUpdated, ToolName
from app.modules.mcp.tools.support import (
    CHANGES_DATA,
    PAYMENT_METHODS,
    ExpenseIdArg,
    given,
    require_arguments,
    tool_errors,
)
from app.modules.mcp.tools.budget_watch import BUDGET_ALERTS_NOTE, watch_budgets
from app.modules.mcp.tools.context import ToolContext


def register_update_expense(server: MCPServer, context: ToolContext) -> None:
    """Add the update_expense tool: change only the fields given (UpdateExpense) and answer with the result.

    Raises RuntimeError at start-up if the tool lacks an argument the contract names (expense_id,
    clear_note).
    """
    views, recorder = context.views, context.recorder

    # Changes some fields. An argument left as "" (or False) means "keep it"; the handler raises the
    # expense's version by one, so a delete approved for the old version is refused afterwards.
    @server.tool(
        name=ToolName.UPDATE_EXPENSE,
        annotations=CHANGES_DATA,
        description="Change some fields of an existing expense. Only pass the fields that should change. "
        f"To remove the note, pass {CLEAR_NOTE_ARGUMENT}=true. " + BUDGET_ALERTS_NOTE,
    )
    def update_expense(
        expense_id: ExpenseIdArg,
        amount: Annotated[str | float, Field(description="New amount, e.g. '450.50'.")] = "",
        category: Annotated[str, Field(description="New category name.")] = "",
        merchant: Annotated[str, Field(description="New merchant.")] = "",
        spent_on: Annotated[str, Field(description="New date as YYYY-MM-DD.")] = "",
        payment_method: Annotated[str, Field(description=f"New payment method: {PAYMENT_METHODS}.")] = "",
        currency: Annotated[str, Field(description="New ISO currency code, e.g. INR.")] = "",
        note: Annotated[str, Field(description="New note.")] = "",
        clear_note: Annotated[bool, Field(description="true to remove the note.")] = False,
    ) -> ExpenseUpdated:
        with tool_errors():
            # Only the caller's own expense can change; another person's is "not found" (caller.py, D191).
            owner = current_caller()
            sent = {
                "amount": given(str(amount)),
                "merchant": given(merchant),
                "spent_on": given(spent_on),
                "payment_method": given(payment_method),
                "currency": given(currency),
                "note": given(note),
            }
            # Only the fields that were given change; everything else stays as it was.
            changes = {field: value for field, value in sent.items() if value is not None}
            if given(category):
                changes["category_id"] = views.category_id(category)
            if clear_note:
                changes["note"] = None
            if not changes:
                # Saying "updated" when nothing changed would mislead the caller (and the user).
                raise BusinessRuleError("Nothing to change: pass at least one field to update.")
            checked = expenses.ExpenseChanges(**changes)
            # The month whose budgets can only go up: the new date's, or the expense's own (D211).
            day = checked.spent_on or views.find(owner, expense_id).spent_on
            # Through the recorder: a new amount, currency or date is converted to INR again (D204).
            _, alerts = watch_budgets(context.bus, owner, day, lambda: recorder.update(owner, expense_id, checked))
            return ExpenseUpdated(updated=views.find(owner, expense_id), budget_alerts=alerts)

    require_arguments(update_expense, EXPENSE_ID_ARGUMENT, CLEAR_NOTE_ARGUMENT)
