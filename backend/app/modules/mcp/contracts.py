"""The MCP server's contract: tool names, argument names, resource addresses, and every tool's result.

Each tool returns one of the models below. The MCP SDK publishes its JSON Schema as the tool's
`outputSchema` and sends the result as `structuredContent`, so any client (the assistant included)
gets typed data instead of guessing at keys inside a JSON string.

This file has no server code, so a client can import it without loading the server. It is the mcp
module's contract layer: the package's __init__.py exports all of it. Used by the server's own files
and by the assistant, which calls the tools by these names and reads their typed results.

The Pydantic models and enums below are part of the published schemas (their docstrings become schema
descriptions), so notes for people reading the code are `#` comments.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.modules.expenses import MonthlySummary, MonthTotal, PaymentMethod

# How a client authenticates to /mcp/ over HTTP: "Authorization: Bearer <personal access token>" (D191).
AUTHORIZATION_HEADER = "Authorization"
BEARER_SCHEME = "Bearer"

# The name the server gives clients when they connect.
SERVER_NAME = "spendwise"


# Every tool's name, in one place: the server registers the tools under these names, and the assistant
# calls them, labels them and picks their cards by them.
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


# Where each resource lives. The assistant reads CATEGORIES to learn the category names.
class ResourceUri(StrEnum):
    CATEGORIES = "expenses://categories"
    RECENT = "expenses://recent"


# How every tool and the "recent" resource show an expense (views.to_view builds it from ExpenseRead).
class ExpenseView(BaseModel):
    """An expense as the tools show it: the category by name, the amount in rupees."""

    model_config = ConfigDict(frozen=True)

    id: int
    amount: Decimal
    currency: str
    # The same amount in INR (D204): what totals count. Equal to `amount` for INR; null only for an expense in another
    # currency saved before it could be converted. The name says the currency, for the model reading it.
    amount_in_inr: Decimal | None
    category: str
    merchant: str
    note: str | None
    spent_on: date
    payment_method: PaymentMethod
    version: int  # raised on every change; pass it to delete_expense as expected_version


# add_expense's result: the expense as stored.
class ExpenseSaved(BaseModel):
    saved: ExpenseView


# get_expense's result.
class ExpenseFound(BaseModel):
    expense: ExpenseView


# update_expense's result: the expense after the change (its version raised by one).
class ExpenseUpdated(BaseModel):
    updated: ExpenseView


# delete_expense's result: the expense as it was just before it was deleted.
class ExpenseDeleted(BaseModel):
    deleted: ExpenseView


# list_expenses's result: at most MAX_ROWS (tools/list_expenses.py) expenses, newest first.
class ExpenseSearch(BaseModel):
    # How many match in total; `expenses` holds at most the newest few of them.
    count: int
    expenses: list[ExpenseView]
    # True when more matched than `expenses` holds, so the model knows to narrow the filters.
    truncated: bool


# get_summary's result. Built on the expenses module's own summary, so both answers stay the same shape.
class MonthSpending(MonthlySummary):
    """One month's spending (see expenses.MonthlySummary), plus the month before, for comparison."""

    previous_month: MonthTotal
