"""Business rules for expenses. Every caller (API, seed, later the MCP tools) goes through here.

Returns DTOs (ExpenseRead, MonthlySummary), never table rows. Raises NotFoundError and
BusinessRuleError, which the API turns into 404 and 422.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.money import DEFAULT_CURRENCY, rupees_to_paise

# The categories module's public interface: the only way in to another module.
from app.modules import categories
from app.modules.expenses import repository
from app.modules.expenses.models import Expense
from app.modules.expenses.schemas import (
    CategoryTotal,
    ExpenseCreate,
    ExpenseFilters,
    ExpenseRead,
    ExpenseUpdate,
    MonthlySummary,
)


def _check_amount(amount: Decimal) -> None:
    # A business rule, not a format rule: zero or negative amounts aren't expenses.
    if amount <= 0:
        raise BusinessRuleError("Amount must be greater than 0")


def _check_category(session: Session, category_id: int) -> None:
    # Ask the categories module whether the category exists, instead of reading its table.
    if categories.get_category(session, category_id) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")


def _get_or_raise(session: Session, expense_id: int) -> Expense:
    expense = repository.get(session, expense_id)
    if expense is None:
        raise NotFoundError(f"Expense {expense_id} not found")
    return expense


def create_expense(session: Session, data: ExpenseCreate) -> ExpenseRead:
    _check_amount(data.amount)
    _check_category(session, data.category_id)
    expense = Expense(amount_minor=rupees_to_paise(data.amount), **data.model_dump(exclude={"amount"}))
    return ExpenseRead.model_validate(repository.add(session, expense))


def get_expense(session: Session, expense_id: int) -> ExpenseRead:
    return ExpenseRead.model_validate(_get_or_raise(session, expense_id))


def list_expenses(session: Session, filters: ExpenseFilters | None = None) -> list[ExpenseRead]:
    rows = repository.search(session, filters or ExpenseFilters())
    return [ExpenseRead.model_validate(e) for e in rows]


def update_expense(session: Session, expense_id: int, data: ExpenseUpdate) -> ExpenseRead:
    expense = _get_or_raise(session, expense_id)
    # Only the fields the caller actually sent; anything left out stays as it was.
    changes = data.model_dump(exclude_unset=True)
    if "amount" in changes:
        _check_amount(changes["amount"])
        changes["amount_minor"] = rupees_to_paise(changes.pop("amount"))
    if "category_id" in changes:
        _check_category(session, changes["category_id"])
    return ExpenseRead.model_validate(repository.update(session, expense, changes))


def delete_expense(session: Session, expense_id: int) -> None:
    repository.delete(session, _get_or_raise(session, expense_id))


def monthly_summary(session: Session, year: int, month: int, currency: str = DEFAULT_CURRENCY) -> MonthlySummary:
    start = date(year, month, 1)
    # The first day of the next month. Querying "before that day" avoids working out month lengths.
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    rows = repository.totals_by_category(session, start, end, currency)

    # Names come from the categories module. With no foreign key, a category could disappear
    # later, so fall back to "Unknown" instead of failing the whole summary.
    names = {c.id: c.name for c in categories.list_categories(session)}
    by_category = [
        CategoryTotal(category_id=cid, category_name=names.get(cid, "Unknown"), expense_count=count, total_minor=total)
        for cid, count, total in rows
    ]
    by_category.sort(key=lambda t: t.total_minor, reverse=True)

    return MonthlySummary(
        month=f"{year:04d}-{month:02d}",
        currency=currency,
        expense_count=sum(t.expense_count for t in by_category),
        total_minor=sum(t.total_minor for t in by_category),
        by_category=by_category,
    )
