"""The SpendWise MCP server: tools (actions) and resources (read-only data) for any MCP client.

Every tool is a thin wrapper over the expenses and categories modules' PUBLIC interfaces, so
MCP callers get exactly the same business rules as the REST API. An MCP client reads each
tool's docstring and parameter descriptions to decide when and how to call it.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

# The official MCP SDK. In SDK 2.x the class formerly called FastMCP is named MCPServer.
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlmodel import Session

from app.core.db import engine
from app.core.errors import BusinessRuleError, NotFoundError

# Other modules' public interfaces only: never their repositories or models.
from app.modules import categories, expenses

server = MCPServer(
    "spendwise",
    instructions="Tools and resources for one person's expense tracker. Amounts are in rupees (INR) by default.",
)

# Each listed row is sent to the client's model and costs tokens, so lists are capped.
MAX_ROWS = 50
RECENT_ROWS = 20

# MCP tool annotations: hints telling clients what a tool does to data. The assistant uses
# read_only_hint to know when the pages must refresh; other clients (e.g. Claude Desktop) may use
# them to decide when to ask the user first. Hints only: a client should trust them from its own servers.
READS_ONLY = ToolAnnotations(read_only_hint=True)
ADDS_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=False)
CHANGES_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=True)  # overwrites or removes


@contextmanager
def _tool_session() -> Iterator[Session]:
    """A database session for one tool call, with expected problems reported to the client.

    MCP calls don't go through FastAPI's request handling, so each tool opens its own session.
    The SDK hides the text of unexpected exceptions from clients (it could leak internals) and
    only passes on a ToolError's message. Our expected errors (unknown category, amount <= 0,
    bad date, missing expense) are safe and useful to show, so they become ToolErrors.
    """
    with Session(engine) as session:
        try:
            yield session
        except (BusinessRuleError, NotFoundError, ValueError) as exc:  # ValueError covers Pydantic's ValidationError
            raise ToolError(str(exc)) from exc


def _category_names(session: Session) -> dict[int, str]:
    return {c.id: c.name for c in categories.list_categories(session)}


def _category_id(session: Session, name: str) -> int:
    names = _category_names(session)
    for category_id, category_name in names.items():
        if category_name.lower() == name.lower():
            return category_id
    raise BusinessRuleError(f"Unknown category '{name}'. Use one of: {', '.join(names.values())}.")


def _describe(expense: expenses.ExpenseRead, names: dict[int, str]) -> dict[str, Any]:
    return {
        "id": expense.id,
        "amount": str(expense.amount),
        "currency": expense.currency,
        "category": names.get(expense.category_id, "Unknown"),
        "merchant": expense.merchant,
        "note": expense.note,
        "spent_on": expense.spent_on.isoformat(),
        "payment_method": expense.payment_method.value,
    }


# ---------- tools: actions a client's model can ask for ----------


@server.tool(annotations=ADDS_DATA)
def add_expense(
    amount: Annotated[str, Field(description="Amount as a plain number string, e.g. '450.50'.")],
    category: Annotated[str, Field(description="Category name; see the expenses://categories resource.")],
    merchant: Annotated[str, Field(description="The shop, company or person paid.")],
    spent_on: Annotated[str, Field(description="Date of the expense as YYYY-MM-DD.")],
    payment_method: Annotated[str, Field(description="One of: cash, upi, card, netbanking, wallet, other.")],
    note: Annotated[str | None, Field(description="Optional short note about what was bought.")] = None,
    currency: Annotated[str, Field(description="ISO currency code. INR unless stated otherwise.")] = "INR",
) -> dict[str, Any]:
    """Record a new expense. Needs the amount, category, merchant, date and payment method;
    if any is unknown, ask the user instead of guessing."""
    with _tool_session() as session:
        created = expenses.create_expense(
            session,
            expenses.ExpenseCreate(
                amount=amount,
                currency=currency,
                category_id=_category_id(session, category),
                merchant=merchant,
                note=note,
                spent_on=spent_on,
                payment_method=payment_method,
            ),
        )
        return {"saved": _describe(created, _category_names(session))}


@server.tool(annotations=READS_ONLY)
def list_expenses(
    start_date: Annotated[str | None, Field(description="Only expenses on or after this date (YYYY-MM-DD).")] = None,
    end_date: Annotated[str | None, Field(description="Only expenses on or before this date (YYYY-MM-DD).")] = None,
    category: Annotated[str | None, Field(description="Only this category (by name).")] = None,
    merchant: Annotated[str | None, Field(description="Only this exact merchant (any letter case).")] = None,
    search: Annotated[str | None, Field(description="Only expenses whose merchant or note contains this text.")] = None,
) -> dict[str, Any]:
    """List expenses, newest first, optionally filtered. Use it to find expense ids before
    updating or deleting, and to answer questions about specific expenses."""
    with _tool_session() as session:
        filters = expenses.ExpenseFilters(
            start_date=start_date,
            end_date=end_date,
            category_id=_category_id(session, category) if category else None,
            merchant=merchant,
            search=search,
        )
        rows = expenses.list_expenses(session, filters)
        names = _category_names(session)
        return {
            "count": len(rows),
            "expenses": [_describe(e, names) for e in rows[:MAX_ROWS]],
            "truncated": len(rows) > MAX_ROWS,
        }


@server.tool(annotations=READS_ONLY)
def get_summary(
    month: Annotated[str, Field(description="The month as YYYY-MM, e.g. '2026-11'.", pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    currency: Annotated[str, Field(description="ISO currency code. INR unless asked otherwise.")] = "INR",
) -> dict[str, Any]:
    """Get one month's total spending and the total for each category, biggest first, plus the
    previous month's total for comparison. Use it for questions like "where did my money go?"."""
    year, month_number = (int(part) for part in month.split("-"))
    previous_year, previous_number = (year, month_number - 1) if month_number > 1 else (year - 1, 12)
    with _tool_session() as session:
        summary = expenses.monthly_summary(session, year, month_number, currency)
        previous = expenses.monthly_summary(session, previous_year, previous_number, currency)
        # mode="json" turns Decimals into strings like "450.50".
        result = summary.model_dump(mode="json")
        # Added alongside the existing fields, so clients that read the old shape keep working.
        result["previous_month"] = {
            "month": f"{previous_year}-{previous_number:02d}",
            "total": str(previous.total),
            "expense_count": previous.expense_count,
        }
        return result


@server.tool(annotations=CHANGES_DATA)
def update_expense(
    expense_id: Annotated[int, Field(description="The id of the expense to change (find it with list_expenses).")],
    amount: Annotated[str | None, Field(description="New amount as a plain number string.")] = None,
    category: Annotated[str | None, Field(description="New category name.")] = None,
    merchant: Annotated[str | None, Field(description="New merchant.")] = None,
    spent_on: Annotated[str | None, Field(description="New date as YYYY-MM-DD.")] = None,
    payment_method: Annotated[str | None, Field(description="New payment method.")] = None,
    note: Annotated[str | None, Field(description="New note.")] = None,
) -> dict[str, Any]:
    """Change some fields of an existing expense. Only pass the fields that should change."""
    with _tool_session() as session:
        changes: dict[str, Any] = {
            "amount": amount,
            "merchant": merchant,
            "spent_on": spent_on,
            "payment_method": payment_method,
            "note": note,
        }
        if category:
            changes["category_id"] = _category_id(session, category)
        # Leave out arguments that weren't passed, so only those fields change.
        update = expenses.ExpenseUpdate(**{k: v for k, v in changes.items() if v is not None})
        updated = expenses.update_expense(session, expense_id, update)
        return {"updated": _describe(updated, _category_names(session))}


@server.tool(annotations=CHANGES_DATA)
def delete_expense(
    expense_id: Annotated[int, Field(description="The id of the expense to delete (find it with list_expenses).")],
    confirmed: Annotated[bool, Field(description="true only after the user has explicitly confirmed.")] = False,
) -> dict[str, Any]:
    """Delete an expense permanently. Call it first with confirmed=false: nothing is deleted, and
    the expense comes back so you can show it to the user. Call again with confirmed=true only
    after the user has clearly agreed to delete that expense."""
    with _tool_session() as session:
        expense = expenses.get_expense(session, expense_id)
        details = _describe(expense, _category_names(session))
        # The safety rule "confirm before deletes": without confirmation, just report what would go.
        if not confirmed:
            return {"deleted": False, "needs_confirmation": True, "expense": details}
        expenses.delete_expense(session, expense_id)
        return {"deleted": True, "expense": details}


# ---------- resources: read-only data a client can load as context ----------


@server.resource("expenses://categories", mime_type="application/json")
def categories_resource() -> str:
    """The expense categories that exist (id, name, icon)."""
    with Session(engine) as session:
        return json.dumps([c.model_dump() for c in categories.list_categories(session)])


@server.resource("expenses://recent", mime_type="application/json")
def recent_expenses_resource() -> str:
    """The most recent expenses, newest first."""
    with Session(engine) as session:
        names = _category_names(session)
        rows = expenses.list_expenses(session)[:RECENT_ROWS]
        return json.dumps([_describe(e, names) for e in rows])
