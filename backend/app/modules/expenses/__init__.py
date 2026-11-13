"""Expenses module: money spent, with amount, category, merchant and date.

Public interface: other modules import ONLY the names below, from `app.modules.expenses`.
Models, repository, router and service internals stay private to this module.
"""

from app.modules.expenses.schemas import (
    CategoryTotal,
    ExpenseCreate,
    ExpenseFilters,
    ExpenseRead,
    ExpenseUpdate,
    MonthlySummary,
    PaymentMethod,
)
from app.modules.expenses.service import (
    create_expense,
    delete_expense,
    get_expense,
    list_expenses,
    monthly_summary,
    update_expense,
)

__all__ = [
    "CategoryTotal",
    "ExpenseCreate",
    "ExpenseFilters",
    "ExpenseRead",
    "ExpenseUpdate",
    "MonthlySummary",
    "PaymentMethod",
    "create_expense",
    "delete_expense",
    "get_expense",
    "list_expenses",
    "monthly_summary",
    "update_expense",
]
