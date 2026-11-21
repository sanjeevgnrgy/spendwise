"""The add_expense MCP tool: record a new expense, and answer with it as stored.

Part of the mcp adapter. register_add_expense adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it turns its arguments into the expenses module's
NewExpense, saved through the expenses module's recorder (which converts an amount in another currency to INR
first, D204), so MCP callers get exactly the REST API's rules (amount > 0, the category must exist, a currency that
can be converted), then answers with the saved expense (ExpenseSaved) and the budgets it pushed near or over their
limit (the budgets module's BudgetWatch).

What clients see comes from the tool function: the SDK builds the input schema (titled
"add_expenseArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.money import CURRENCY_PATTERN, DEFAULT_CURRENCY
from app.modules import expenses
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ExpenseSaved, ResourceUri, ToolName
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.support import ADDS_DATA, BUDGET_ALERTS_NOTE, PAYMENT_METHODS, given, tool_errors


def register_add_expense(server: MCPServer, context: ToolContext) -> None:
    """Add the add_expense tool: record a new expense (CreateExpense) and answer with it.

    The category arrives as a name and is turned into an id first, so an unknown name is a tool error that
    lists the real ones. The expenses module checks the rest; its errors reach the client as tool errors.
    """
    views, recorder = context.views, context.recorder

    # Records an expense. The command validates the amount (rupees, at most 2 decimals, stored as paise)
    # and the date; the handler refuses an amount <= 0 or a category that doesn't exist.
    @server.tool(
        name=ToolName.ADD_EXPENSE,
        annotations=ADDS_DATA,
        description="Record a new expense. Needs the amount, category, merchant, date and payment method; "
        "if any is unknown, ask the user instead of guessing. " + BUDGET_ALERTS_NOTE,
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
            str,
            Field(
                description="ISO currency code. INR unless stated otherwise; another currency is also stored in INR.",
                pattern=CURRENCY_PATTERN,
            ),
        ] = DEFAULT_CURRENCY,
    ) -> ExpenseSaved:
        with tool_errors():
            # The caller's own expense: the person behind the token or the signed-in run (caller.py), never an
            # argument (D191).
            owner = current_caller()
            new = expenses.NewExpense.model_validate(
                {
                    "amount": str(amount),
                    "currency": currency,
                    "category_id": views.category_id(category),
                    "merchant": merchant,
                    "note": given(note),
                    "spent_on": spent_on,
                    "payment_method": payment_method,
                }
            )
            # Saved between two looks at the month's budgets, so the answer can say which ones it pushed near or over
            # their limit (D211).
            expense_id, alerts = context.budget_watch.around(owner, new.spent_on, lambda: recorder.create(owner, new))
            return ExpenseSaved(saved=views.find(owner, expense_id), budget_alerts=alerts)
