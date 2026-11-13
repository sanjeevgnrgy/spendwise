"""Tools the assistant's model may call: thin wrappers over the expenses module's public interface.

The model reads each docstring to decide WHEN to call a tool, and each argument's
Annotated description to know WHAT to pass (agent.py turns these into Gemini's tool
declarations). Arguments are plain strings and numbers, because they arrive as JSON from
the model; the expenses module validates them, exactly as it does for the REST API.
Every tool returns a small JSON-friendly dict, which is sent back to the model.
"""

from typing import Annotated, Any

from sqlmodel import Session

from app.core.errors import BusinessRuleError

# Other modules' public interfaces only: never their repositories or models.
from app.modules import categories, expenses

# Each listed row is sent back to the model and costs tokens, so lists are capped.
MAX_ROWS = 50


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


def add_expense(
    session: Session,
    amount: Annotated[str, "Amount as a plain number string, e.g. '450.50'."],
    category: Annotated[str, "Category name, exactly as in the category list."],
    merchant: Annotated[str, "The shop, company or person paid."],
    spent_on: Annotated[str, "Date of the expense as YYYY-MM-DD."],
    payment_method: Annotated[str, "One of: cash, upi, card, netbanking, wallet, other."],
    note: Annotated[str | None, "Optional short note about what was bought."] = None,
    currency: Annotated[str, "ISO currency code. INR unless the user says otherwise."] = "INR",
) -> dict[str, Any]:
    """Record a new expense. Only call this when you know the amount, category, merchant, date and
    payment method; if any of them is missing, ask the user instead of guessing."""
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


def list_expenses(
    session: Session,
    start_date: Annotated[str | None, "Only expenses on or after this date (YYYY-MM-DD)."] = None,
    end_date: Annotated[str | None, "Only expenses on or before this date (YYYY-MM-DD)."] = None,
    category: Annotated[str | None, "Only this category (a name from the category list)."] = None,
    merchant: Annotated[str | None, "Only this exact merchant (any letter case)."] = None,
    search: Annotated[str | None, "Only expenses whose merchant or note contains this text."] = None,
) -> dict[str, Any]:
    """List expenses, newest first, optionally filtered. Use this to find expense ids before
    updating or deleting, and to answer questions about specific expenses."""
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


def get_summary(
    session: Session,
    month: Annotated[str, "The month as YYYY-MM, e.g. '2026-11'."],
    currency: Annotated[str, "ISO currency code. INR unless the user asks about another currency."] = "INR",
) -> dict[str, Any]:
    """Get one month's total spending and the total for each category, biggest first."""
    year, month_number = (int(part) for part in month.split("-"))
    summary = expenses.monthly_summary(session, year, month_number, currency)
    # mode="json" turns Decimals into strings like "450.50" for the model.
    return summary.model_dump(mode="json")


def update_expense(
    session: Session,
    expense_id: Annotated[int, "The id of the expense to change (find it with list_expenses)."],
    amount: Annotated[str | None, "New amount as a plain number string, e.g. '450.50'."] = None,
    category: Annotated[str | None, "New category name from the category list."] = None,
    merchant: Annotated[str | None, "New merchant."] = None,
    spent_on: Annotated[str | None, "New date as YYYY-MM-DD."] = None,
    payment_method: Annotated[str | None, "New payment method: cash, upi, card, netbanking, wallet or other."] = None,
    note: Annotated[str | None, "New note."] = None,
) -> dict[str, Any]:
    """Change some fields of an existing expense. Only pass the fields that should change."""
    changes: dict[str, Any] = {
        "amount": amount,
        "merchant": merchant,
        "spent_on": spent_on,
        "payment_method": payment_method,
        "note": note,
    }
    if category:
        changes["category_id"] = _category_id(session, category)
    # Leave out arguments the model didn't pass, so only those fields change.
    update = expenses.ExpenseUpdate(**{k: v for k, v in changes.items() if v is not None})
    updated = expenses.update_expense(session, expense_id, update)
    return {"updated": _describe(updated, _category_names(session))}


def delete_expense(
    session: Session,
    expense_id: Annotated[int, "The id of the expense to delete (find it with list_expenses)."],
    confirmed: Annotated[bool, "true only after the user has explicitly confirmed this deletion."] = False,
) -> dict[str, Any]:
    """Delete an expense permanently. Call it first with confirmed=false: nothing is deleted, and you
    get the expense back to show the user and ask them to confirm. Call again with confirmed=true
    only after the user has clearly said yes to deleting that expense."""
    expense = expenses.get_expense(session, expense_id)
    details = _describe(expense, _category_names(session))
    # The safety rule "confirm before deletes": without confirmation, just report what would go.
    if not confirmed:
        return {"deleted": False, "needs_confirmation": True, "expense": details}
    expenses.delete_expense(session, expense_id)
    return {"deleted": True, "expense": details}
