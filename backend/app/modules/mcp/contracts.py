"""The MCP server's contract: tool names, argument names, resource addresses, and every tool's result.

Each tool returns one of the models below. The MCP SDK publishes its JSON Schema as the tool's
`outputSchema` and sends the result as `structuredContent`, so any client (the assistant included)
gets typed data instead of guessing at keys inside a JSON string.

This file has no server code, so a client can import it without loading the server.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.modules.expenses import MonthlySummary, MonthTotal, PaymentMethod

SERVER_NAME = "spendwise"


class ToolName(StrEnum):
    ADD_EXPENSE = "add_expense"
    LIST_EXPENSES = "list_expenses"
    GET_EXPENSE = "get_expense"
    GET_SUMMARY = "get_summary"
    UPDATE_EXPENSE = "update_expense"
    DELETE_EXPENSE = "delete_expense"


# Argument names other code refers to. The server checks at start-up that its tools really have them.
EXPENSE_ID_ARGUMENT = "expense_id"
# delete_expense's required interlock: only a real `true` deletes.
CONFIRM_ARGUMENT = "confirmed"
# delete_expense's optional precondition: delete only if the expense is still at this version.
EXPECTED_VERSION_ARGUMENT = "expected_version"
# update_expense's switch for removing the note.
CLEAR_NOTE_ARGUMENT = "clear_note"


class ResourceUri(StrEnum):
    CATEGORIES = "expenses://categories"
    RECENT = "expenses://recent"


class ExpenseView(BaseModel):
    """An expense as the tools show it: the category by name, the amount in rupees."""

    model_config = ConfigDict(frozen=True)

    id: int
    amount: Decimal
    currency: str
    category: str
    merchant: str
    note: str | None
    spent_on: date
    payment_method: PaymentMethod
    version: int  # raised on every change; pass it to delete_expense as expected_version


class ExpenseSaved(BaseModel):
    saved: ExpenseView


class ExpenseFound(BaseModel):
    expense: ExpenseView


class ExpenseUpdated(BaseModel):
    updated: ExpenseView


class ExpenseDeleted(BaseModel):
    deleted: ExpenseView


class ExpenseSearch(BaseModel):
    # How many match in total; `expenses` holds at most the newest few of them.
    count: int
    expenses: list[ExpenseView]
    truncated: bool


class MonthSpending(MonthlySummary):
    """One month's spending (see expenses.MonthlySummary), plus the month before, for comparison."""

    previous_month: MonthTotal
