"""Expenses module: money spent, with amount, category, merchant and date.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.expenses`, and send them through the bus. Tables, handlers, the repository and the router
stay private; the composition root (bootstrap.py) plugs them in through module.py.

Who uses it: the MCP server (every command and query, behind its tools), the assistant (PaymentMethod
and PAYMENT_METHOD_LABELS for its forms) and seed.py (CreateExpense, ListExpenses).
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
