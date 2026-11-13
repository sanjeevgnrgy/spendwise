"""Expenses module: money spent, with amount, category, merchant and date.

Public interface: other modules import ONLY the contract names below, from `app.modules.expenses`,
and send them through the bus. Tables, handlers, the repository and the router stay private.
"""

from app.modules.expenses.contracts import (
    MAX_LIST_LIMIT,
    PAYMENT_METHOD_LABELS,
    CategoryTotal,
    CreateExpense,
    DeleteExpense,
    ExpenseChanges,
    ExpenseId,
    ExpenseList,
    ExpenseRead,
    GetExpense,
    GetMonthlySummary,
    GetMonthlyTrend,
    ListExpenses,
    MonthlySummary,
    MonthlyTrend,
    MonthTotal,
    PaymentMethod,
    UpdateExpense,
)

__all__ = [
    "MAX_LIST_LIMIT",
    "PAYMENT_METHOD_LABELS",
    "CategoryTotal",
    "CreateExpense",
    "DeleteExpense",
    "ExpenseChanges",
    "ExpenseId",
    "ExpenseList",
    "ExpenseRead",
    "GetExpense",
    "GetMonthlySummary",
    "GetMonthlyTrend",
    "ListExpenses",
    "MonthTotal",
    "MonthlySummary",
    "MonthlyTrend",
    "PaymentMethod",
    "UpdateExpense",
]
