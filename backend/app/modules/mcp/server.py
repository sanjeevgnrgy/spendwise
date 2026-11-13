"""The SpendWise MCP server: tools (actions) and resources (read-only data) for any MCP client.

Every tool is a thin adapter: it turns an MCP call into commands and queries for the expenses and
categories modules, sent through the bus, so MCP callers get exactly the same rules as the REST API.
An MCP client reads each tool's description and parameter descriptions to decide when and how to call it.
"""

import inspect
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Annotated, Any

# The official MCP SDK. In SDK 2.x the class formerly called FastMCP is named MCPServer.
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, ValidationError
from sqlalchemy.exc import OperationalError

from app.core.cqrs import MessageBus
from app.core.db import RecordId
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.money import CURRENCY_PATTERN, DEFAULT_CURRENCY
from app.core.months import YearMonth

# Other modules' contracts only: never their tables or handlers.
from app.modules import categories, expenses
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

# Each listed row is sent to the client's model and costs tokens, so lists are capped.
MAX_ROWS = 50
RECENT_ROWS = 20
BUSY = "The database is busy right now; try again in a moment."
# SQLite's own names for "another connection holds the lock": worth a retry, unlike other database errors.
_LOCK_ERRORS = ("SQLITE_BUSY", "SQLITE_LOCKED")

# MCP tool annotations: hints telling clients what a tool does to data. The assistant uses
# read_only_hint to know when the pages must refresh; other clients (e.g. Claude Desktop) may use
# them to decide when to ask the user first. Hints only: a client should trust them from its own servers.
READS_ONLY = ToolAnnotations(read_only_hint=True)
ADDS_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=False)
CHANGES_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=True)  # overwrites or removes

PAYMENT_METHODS = ", ".join(expenses.PaymentMethod)
ExpenseIdArg = Annotated[RecordId, Field(description=f"The expense's id (see {ToolName.LIST_EXPENSES}).")]

# Optional text arguments are plain `str`, with "" meaning "not given". Models often fill unused
# optional strings with "", and the SDK reads non-`str` arguments as JSON first (so the text "null"
# would quietly become None, and "[1, 2]" a list).


def _given(value: str) -> str | None:
    """An optional text argument's value, or None if it wasn't given ("" or only spaces)."""
    return value.strip() or None


def _is_lock_error(exc: OperationalError) -> bool:
    return getattr(exc.orig, "sqlite_errorname", None) in _LOCK_ERRORS


@contextmanager
def _tool_errors() -> Iterator[None]:
    """Report expected problems to the client as tool errors.

    The SDK hides the text of unexpected exceptions from clients (it could leak internals) and only
    passes on a ToolError's message. Our expected errors (unknown category, amount <= 0, bad date,
    missing expense) are safe and useful to show, so they become ToolErrors.
    """
    try:
        yield
    except (BusinessRuleError, NotFoundError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc
    except OperationalError as exc:
        # "Database is locked" (another process, e.g. the stdio server, is writing) is worth a retry. Any
        # other database error (say, a missing table) is a real problem, and must not pass for "busy".
        if _is_lock_error(exc):
            raise ToolError(BUSY) from exc
        raise


def create_server(bus: MessageBus) -> MCPServer:
    """Build the MCP server around a bus. Called once by the composition root (bootstrap.py)."""
    server = MCPServer(
        SERVER_NAME,
        instructions="Tools and resources for one person's expense tracker. Amounts are in rupees (INR) by default.",
    )

    def category_names() -> dict[int, str]:
        return {c.id: c.name for c in bus.ask(categories.ListCategories())}

    def category_id(name: str) -> int:
        found = bus.ask(categories.FindCategoryByName(name=name))
        if found is not None:
            return found.id
        names = category_names().values()
        if not names:
            raise BusinessRuleError(categories.NO_CATEGORIES_YET)
        raise BusinessRuleError(f"Unknown category '{name.strip()}'. Use one of: {', '.join(names)}.")

    def view(expense: expenses.ExpenseRead, names: dict[int, str]) -> ExpenseView:
        return ExpenseView(
            id=expense.id,
            amount=expense.amount,
            currency=expense.currency,
            category=names.get(expense.category_id, categories.UNKNOWN_CATEGORY),
            merchant=expense.merchant,
            note=expense.note,
            spent_on=expense.spent_on,
            payment_method=expense.payment_method,
            version=expense.version,
        )

    def find(expense_id: int) -> ExpenseView:
        return view(bus.ask(expenses.GetExpense(expense_id=expense_id)), category_names())

    # ---------- tools: actions a client's model can ask for ----------

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
        with _tool_errors():
            command = expenses.CreateExpense(
                amount=str(amount),
                currency=currency,
                category_id=category_id(category),
                merchant=merchant,
                note=_given(note),
                spent_on=spent_on,
                payment_method=payment_method,
            )
            return ExpenseSaved(saved=find(bus.execute(command)))

    @server.tool(
        name=ToolName.LIST_EXPENSES,
        annotations=READS_ONLY,
        description="List expenses, newest first, optionally filtered. Use it to find expense ids before "
        "updating or deleting, and to answer questions about specific expenses.",
    )
    def list_expenses(
        start_date: Annotated[str, Field(description="Only expenses on or after this date (YYYY-MM-DD).")] = "",
        end_date: Annotated[str, Field(description="Only expenses on or before this date (YYYY-MM-DD).")] = "",
        category: Annotated[str, Field(description="Only this category (by name).")] = "",
        merchant: Annotated[str, Field(description="Only this exact merchant (any letter case).")] = "",
        search: Annotated[str, Field(description="Only expenses whose merchant or note contains this text.")] = "",
    ) -> ExpenseSearch:
        with _tool_errors():
            category_name = _given(category)
            found = bus.ask(
                expenses.ListExpenses(
                    start_date=_given(start_date),
                    end_date=_given(end_date),
                    category_id=category_id(category_name) if category_name else None,
                    merchant=_given(merchant),
                    search=_given(search),
                    # The database stops after MAX_ROWS and counts the rest, instead of sending every row.
                    limit=MAX_ROWS,
                )
            )
            names = category_names()
            return ExpenseSearch(
                count=found.total,
                expenses=[view(e, names) for e in found.items],
                truncated=found.total > len(found.items),
            )

    @server.tool(
        name=ToolName.GET_EXPENSE,
        annotations=READS_ONLY,
        description="Get one expense by its id, e.g. to show it to the user before changing or deleting it.",
    )
    def get_expense(expense_id: ExpenseIdArg) -> ExpenseFound:
        with _tool_errors():
            return ExpenseFound(expense=find(expense_id))

    @server.tool(
        name=ToolName.GET_SUMMARY,
        annotations=READS_ONLY,
        description="Get one month's total spending and the total for each category, biggest first, plus the "
        'previous month\'s total for comparison. Use it for questions like "where did my money go?".',
    )
    def get_summary(
        month: Annotated[str, Field(description="The month as YYYY-MM, e.g. '2026-11'.", pattern=YearMonth.PATTERN)],
        currency: Annotated[
            str, Field(description="ISO currency code. INR unless asked otherwise.", pattern=CURRENCY_PATTERN)
        ] = DEFAULT_CURRENCY,
    ) -> MonthSpending:
        with _tool_errors():
            this_month = YearMonth.parse(month)
            summary = bus.ask(expenses.GetMonthlySummary(month=this_month, currency=currency))
            previous = bus.ask(expenses.GetMonthlySummary(month=this_month.shift(-1), currency=currency))
            return MonthSpending(
                **summary.model_dump(exclude={"total"}),
                previous_month=expenses.MonthTotal(
                    month=previous.month, expense_count=previous.expense_count, total_minor=previous.total_minor
                ),
            )

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
        with _tool_errors():
            given = {
                "amount": _given(str(amount)),
                "merchant": _given(merchant),
                "spent_on": _given(spent_on),
                "payment_method": _given(payment_method),
                "currency": _given(currency),
                "note": _given(note),
            }
            # Only the fields that were given change; everything else stays as it was.
            changes = {field: value for field, value in given.items() if value is not None}
            if _given(category):
                changes["category_id"] = category_id(category)
            if clear_note:
                changes["note"] = None
            if not changes:
                # Saying "updated" when nothing changed would mislead the caller (and the user).
                raise BusinessRuleError("Nothing to change: pass at least one field to update.")
            bus.execute(expenses.UpdateExpense(expense_id=expense_id, changes=expenses.ExpenseChanges(**changes)))
            return ExpenseUpdated(updated=find(expense_id))

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
        with _tool_errors():
            if confirmed is not True:
                raise BusinessRuleError(f"Nothing was deleted: {CONFIRM_ARGUMENT} must be true, after the user has agreed.")
            expense = find(expense_id)
            bus.execute(expenses.DeleteExpense(expense_id=expense_id, expected_version=expected_version))
            return ExpenseDeleted(deleted=expense)

    # ---------- resources: read-only data a client can load as context ----------

    @server.resource(ResourceUri.CATEGORIES, mime_type="application/json")
    def categories_resource() -> str:
        """The expense categories that exist (id, name, icon)."""
        return json.dumps([c.model_dump() for c in bus.ask(categories.ListCategories())])

    @server.resource(ResourceUri.RECENT, mime_type="application/json")
    def recent_expenses_resource() -> str:
        """The most recent expenses, newest first."""
        names = category_names()
        rows = bus.ask(expenses.ListExpenses(limit=RECENT_ROWS)).items
        return json.dumps([view(e, names).model_dump(mode="json") for e in rows])

    # The contract names arguments other code relies on (the assistant sends them): fail at start-up, not
    # at the first call, if a tool's parameters don't match.
    _require_arguments(delete_expense, EXPENSE_ID_ARGUMENT, CONFIRM_ARGUMENT, EXPECTED_VERSION_ARGUMENT)
    _require_arguments(get_expense, EXPENSE_ID_ARGUMENT)
    _require_arguments(update_expense, EXPENSE_ID_ARGUMENT, CLEAR_NOTE_ARGUMENT)
    return server


def _require_arguments(tool: Callable[..., Any], *names: str) -> None:
    missing = set(names) - set(inspect.signature(tool).parameters)
    if missing:
        raise RuntimeError(f"MCP tool {tool.__name__} lacks the arguments its contract names: {sorted(missing)}")
