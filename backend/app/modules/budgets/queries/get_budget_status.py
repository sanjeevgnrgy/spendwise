"""GetBudgetStatus: a month's spending against a person's budgets. The query, its handler and its answer.

A slice of the budgets module's read side; it never changes anything. module.py registers the handler with the bus.
The month's spending comes from the expenses module's GetMonthlySummary (in INR, every currency counted through its
INR amount, D204) and the category names from the categories module's ListCategories, both through the bus; only
the limits are read from this module's own table. Asked by GET /budgets (the Budgets page and the Dashboard's
budget card) and, in part 2, by the assistant. The answer is a REST response, so notes about it are `#` comments.
"""

from decimal import Decimal

from pydantic import BaseModel, Field
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.core.money import BASE_CURRENCY, paise_to_rupees
from app.core.months import YearMonth
from app.modules import categories, expenses
from app.modules.budgets.domain.rules import month_elapsed_percent, standing
from app.modules.budgets.persistence.tables import Budget
from app.modules.budgets.values import BudgetState


# Spending against one budget. Without a budget, only `spent` is set; with one, the limit, what's left (negative once
# over), the share used in percent (one decimal) and the state.
class BudgetLine(BaseModel):
    spent: Decimal
    limit: Decimal | None = None
    remaining: Decimal | None = None
    used_percent: Decimal | None = None
    state: BudgetState | None = None


# One category's line.
class CategoryBudgetLine(BudgetLine):
    category_id: int
    category_name: str


# GetBudgetStatus's answer (GET /budgets): the month, how much of it has gone by (so spending can be compared with
# time: 60% of the budget used with 50% of the month gone), the overall line (the month's total), and a line for
# every category: those with a budget first, most used first, then the others by what was spent.
class BudgetStatus(BaseModel):
    month: str = Field(pattern=YearMonth.PATTERN, examples=["2026-11"])
    currency: str
    month_elapsed_percent: Decimal
    overall: BudgetLine
    categories: list[CategoryBudgetLine]


# Asked by GET /budgets and the dashboard's card (and, in part 2, the assistant): always one person's budgets.
class GetBudgetStatus(Query[BudgetStatus]):
    """The owner's spending in a month against their budgets."""

    owner_id: UserId
    month: YearMonth


def _line(spent_minor: int, limit_minor: int | None) -> dict[str, object]:
    """A BudgetLine's fields for spending against a limit (or no limit), in rupees."""
    fields: dict[str, object] = {"spent": paise_to_rupees(spent_minor)}
    if limit_minor is not None:
        result = standing(spent_minor, limit_minor)
        fields |= {
            "limit": paise_to_rupees(limit_minor),
            "remaining": paise_to_rupees(result.remaining_minor),
            "used_percent": result.used_percent,
            "state": result.state,
        }
    return fields


def _order(line: CategoryBudgetLine) -> tuple[bool, Decimal, Decimal, str]:
    """Budgeted categories first, most used first; then the rest, biggest spending first; then by name."""
    budgeted = line.used_percent is not None
    return (not budgeted, -(line.used_percent or Decimal(0)), -line.spent, line.category_name)


def get_budget_status(ctx: Context, query: GetBudgetStatus) -> BudgetStatus:
    """The month's spending against each of the owner's budgets, overall and per category. A month with no spending
    gives zeros; a budget for a category that no longer exists is left out."""
    summary = ctx.bus.ask(expenses.GetMonthlySummary(owner_id=query.owner_id, month=query.month))
    spent = {line.category_id: line.total_minor for line in summary.by_category}
    rows = ctx.session.exec(select(Budget).where(col(Budget.owner_id) == query.owner_id))
    limits = {row.category_id: row.limit_minor for row in rows}
    lines = [
        CategoryBudgetLine(category_id=category.id, category_name=category.name,
                           **_line(spent.get(category.id, 0), limits.get(category.id)))
        for category in ctx.bus.ask(categories.ListCategories())
    ]
    return BudgetStatus(
        month=str(query.month),
        currency=BASE_CURRENCY,
        month_elapsed_percent=month_elapsed_percent(query.month, ctx.clock.today()),
        overall=BudgetLine(**_line(summary.total_minor, limits.get(None))),
        categories=sorted(lines, key=_order),
    )
