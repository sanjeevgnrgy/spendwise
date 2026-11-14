"""The MCP tools that change expenses: add_expense, update_expense and delete_expense.

Part of the mcp adapter. Each register_* function adds one tool to a server; server.py calls them in the
order clients list the tools. A tool only translates: it turns its arguments into a command for the
expenses module and sends it through the bus, so MCP callers get exactly the REST API's rules (amount > 0,
the category must exist, versions), then answers with the saved expense as an ExpenseView.

What clients see comes from each tool function: the SDK builds the input schema (titled
"<function name>Arguments") from its name, parameters and annotations, and the description from
`description=`. So those stay exactly as they are, and notes about a tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.cqrs import MessageBus
from app.core.errors import BusinessRuleError
from app.core.money import CURRENCY_PATTERN, DEFAULT_CURRENCY
from app.modules import expenses
from app.modules.mcp.contracts import (
    CLEAR_NOTE_ARGUMENT,
    CONFIRM_ARGUMENT,
    EXPECTED_VERSION_ARGUMENT,
    EXPENSE_ID_ARGUMENT,
    ExpenseDeleted,
    ExpenseSaved,
    ExpenseUpdated,
    ResourceUri,
    ToolName,
)
from app.modules.mcp.tool_support import (
    ADDS_DATA,
    CHANGES_DATA,
    PAYMENT_METHODS,
    ExpenseIdArg,
    given,
    require_arguments,
    tool_errors,
)
from app.modules.mcp.views import ExpenseViews


def register_add_expense(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the add_expense tool: record a new expense (CreateExpense) and answer with it.

    The category arrives as a name and is turned into an id first, so an unknown name is a tool error that
    lists the real ones. The expenses module checks the rest; its errors reach the client as tool errors.
    """

    # Records an expense. The command validates the amount (rupees, at most 2 decimals, stored as paise)
    # and the date; the handler refuses an amount <= 0 or a category that doesn't exist.
    @server.tool(
        name=ToolName.ADD_EXPENSE,
        annotations=ADDS_DATA,
        description="Record a new expense. Needs the amount, category, merchant, date and payment method; "
        "if any is unknown, ask the user instead of guessing.",
    )
    def add_expense(
        # A number is accepted too: some clients send 450.5 rather than "450.50".
        amount: Annotated[str | float, Field(description="Amount, e.g. '450.50'.")],
        category: Annotated[str, Field(description=f"Category name; see the {ResourceUri.CATEGORIES} resource.")],
        merchant: Annotated[str, Field(description="The shop, company or person paid.")],
        spent_on: Annotated[str, Field(description="Date of the expense as YYYY-MM-DD.")],
        payment_method: Annotated[str, Field(description=f"One of: {PAYMENT_METHODS}.")],
        note: Annotated[str, Field(description="Optional short note about what was bought.")] = "",
        currency: Annotated[
            str, Field(description="ISO currency code. INR unless stated otherwise.", pattern=CURRENCY_PATTERN)
        ] = DEFAULT_CURRENCY,
    ) -> ExpenseSaved:
        with tool_errors():
            command = expenses.CreateExpense(
                amount=str(amount),
                currency=currency,
                category_id=views.category_id(category),
                merchant=merchant,
                note=given(note),
                spent_on=spent_on,
                payment_method=payment_method,
            )
            return ExpenseSaved(saved=views.find(bus.execute(command)))


def register_update_expense(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the update_expense tool: change only the fields given (UpdateExpense) and answer with the result.

    Raises RuntimeError at start-up if the tool lacks an argument the contract names (expense_id,
    clear_note).
    """

    # Changes some fields. An argument left as "" (or False) means "keep it"; the handler raises the
    # expense's version by one, so a delete approved for the old version is refused afterwards.
    @server.tool(
        name=ToolName.UPDATE_EXPENSE,
        annotations=CHANGES_DATA,
        description="Change some fields of an existing expense. Only pass the fields that should change. "
        f"To remove the note, pass {CLEAR_NOTE_ARGUMENT}=true.",
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
            bus.execute(expenses.UpdateExpense(expense_id=expense_id, changes=expenses.ExpenseChanges(**changes)))
            return ExpenseUpdated(updated=views.find(expense_id))

    require_arguments(update_expense, EXPENSE_ID_ARGUMENT, CLEAR_NOTE_ARGUMENT)


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
