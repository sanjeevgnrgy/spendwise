"""GetMonthlySummary: one month's total and the total per category. The query, its handler and its answer.

A slice of the expenses module's read side; it never changes anything. module.py registers the handler with the
bus. The database groups and adds up (GROUP BY, COUNT, SUM), so only the totals travel to Python. Category names
come from the categories module's ListCategories query, never from its table. CategoryTotal and MonthlySummary are
REST responses and MCP results, so notes about them are `#` comments, not docstrings.
"""

from pydantic import Field
from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.core.money import BASE_CURRENCY
from app.core.months import YearMonth
from app.modules import categories
from app.modules.expenses.models import Totalled
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.queries.month_range import in_month_range


# One category's share of a month, in MonthlySummary.by_category. category_name is "Unknown"
# (categories.UNKNOWN_CATEGORY) if the category no longer exists.
class CategoryTotal(Totalled):
    category_id: int
    category_name: str
    expense_count: int


# GetMonthlySummary's answer (GET /summary): one month's total in the base currency (INR, every expense counted
# through its INR amount, D204), and the total for each category that had spending. The month is "YYYY-MM" text.
class MonthlySummary(Totalled):
    month: str = Field(pattern=YearMonth.PATTERN, examples=["2026-11"])
    currency: str
    expense_count: int
    # Biggest spend first.
    by_category: list[CategoryTotal]


# Asked by GET /summary and by MCP's get_summary (for the month asked about and the one before). The
# month is a YearMonth value, so the handler can work out where it ends.
class GetMonthlySummary(Query[MonthlySummary]):
    """One month's total of the owner's expenses in INR, and the total per category."""

    owner_id: UserId
    month: YearMonth


def get_monthly_summary(ctx: Context, query: GetMonthlySummary) -> MonthlySummary:
    """One month of the owner's spending in INR: the total, and the total per category, biggest first.

    The database groups by category and adds up (GROUP BY, COUNT, SUM); Python only names the
    categories, sorts the few groups and adds them up for the month. A category that no longer exists
    is named "Unknown". A month with no expenses gives a total of 0 and an empty by_category list.
    """
    statement = (
        select(Expense.category_id, func.count(col(Expense.id)), func.sum(Expense.base_amount_minor))
        .where(*in_month_range(query.owner_id, query.month.first_day(), query.month.shift(1).first_day()))
        .group_by(col(Expense.category_id))
    )
    # Names come from the categories module, through its query: its table isn't ours to read.
    names = {c.id: c.name for c in ctx.bus.ask(categories.ListCategories())}
    by_category = sorted(
        (
            CategoryTotal(
                category_id=category_id,
                category_name=names.get(category_id, categories.UNKNOWN_CATEGORY),
                expense_count=count,
                total_minor=total,
            )
            for category_id, count, total in ctx.session.exec(statement)
        ),
        key=lambda t: t.total_minor,
        reverse=True,
    )
    return MonthlySummary(
        month=str(query.month),
        currency=BASE_CURRENCY,
        expense_count=sum(t.expense_count for t in by_category),
        total_minor=sum(t.total_minor for t in by_category),
        by_category=by_category,
    )
