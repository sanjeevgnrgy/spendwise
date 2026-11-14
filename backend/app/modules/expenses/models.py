"""The expenses module's shared read models: ExpenseRead, ExpenseList, and Totalled, the base of every total.

Part of the module's contract layer. ExpenseRead and ExpenseList are what GetExpense and ListExpenses answer
(queries/get_expense.py, queries/list_expenses.py) and what api.py sends; Totalled is the base of the summary's
and the trend's totals (queries/get_monthly_summary.py, queries/get_monthly_trend.py). These are REST responses
and MCP results, so their docstrings are part of the published schemas: notes for people are `#` comments.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.money import paise_to_rupees
from app.modules.expenses.values import PaymentMethod


# What GetExpense and ListExpenses return, and the REST API's expense object. Built straight from a table
# row (from_attributes); frozen, so nobody can change stored data through it.
class ExpenseRead(BaseModel):
    """An expense as callers see it: everything stored, plus the amount in rupees for display."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    # Paise: the exact stored value, safe for arithmetic.
    amount_minor: int
    currency: str
    category_id: int
    merchant: str
    note: str | None
    spent_on: date
    payment_method: PaymentMethod
    created_at: datetime
    version: int

    # A computed field: sent in the JSON (and listed in the schema) as "amount", never stored. No
    # docstring on it: Pydantic would publish that as the field's description.
    @computed_field
    @property
    def amount(self) -> Decimal:
        # Worked out from amount_minor every time, so the two can never disagree.
        return paise_to_rupees(self.amount_minor)


# ListExpenses's answer: one page of expenses, plus how many match in all, so a caller can page through
# them or say "showing 50 of 120".
class ExpenseList(BaseModel):
    items: list[ExpenseRead]
    # How many match the filters in total; `items` may hold fewer (see ListExpenses.limit).
    total: int


# The shared base of every total: CategoryTotal and MonthlySummary (queries/get_monthly_summary.py) and
# MonthTotal (queries/get_monthly_trend.py). Never sent on its own, only through the classes built on it.
class Totalled(BaseModel):
    """A total in paise, plus the same total in rupees, worked out from it."""

    total_minor: int

    # Rupees for display, computed from total_minor so the two never disagree. (A comment, not a
    # docstring: a computed field's docstring becomes its description in the schema.)
    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)
