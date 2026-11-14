"""Expenses module: money spent, with amount, category, merchant and date.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.expenses`, and send them through the bus. Tables, handlers, the repository and the router
stay private; the composition root (bootstrap.py) plugs them in through module.py.

Inside, each command and each query is one file holding the message, its handler and anything only it uses
(commands/, queries/). What several of them share: values.py (limits, PaymentMethod, field types), models.py
(ExpenseRead, ExpenseList, the totals' base), domain/rules.py (business rules) and persistence/ (the table and
the write side's repository). This file only re-exports the contract names from those files.

Who uses it: the MCP server (every command and query, behind its tools), the assistant (PaymentMethod
and payment_method_label for its forms, MAX_NOTE_LENGTH for a receipt's note), the receipts module (PaymentMethod,
in what a receipt is read into) and seed.py (CreateExpense, ListExpenses).
"""

from app.modules.expenses.commands.create_expense import CreateExpense
from app.modules.expenses.commands.delete_expense import DeleteExpense
from app.modules.expenses.commands.update_expense import ExpenseChanges, UpdateExpense
from app.modules.expenses.i18n import ExpenseText, payment_method_label
from app.modules.expenses.models import ExpenseList, ExpenseRead
from app.modules.expenses.queries.get_expense import GetExpense
from app.modules.expenses.queries.get_monthly_summary import CategoryTotal, GetMonthlySummary, MonthlySummary
from app.modules.expenses.queries.get_monthly_trend import GetMonthlyTrend, MonthlyTrend, MonthTotal
from app.modules.expenses.queries.list_expenses import ListExpenses
from app.modules.expenses.values import MAX_LIST_LIMIT, MAX_NOTE_LENGTH, ExpenseId, PaymentMethod

__all__ = [
    "MAX_LIST_LIMIT",
    "MAX_NOTE_LENGTH",
    "CategoryTotal",
    "CreateExpense",
    "DeleteExpense",
    "ExpenseChanges",
    "ExpenseId",
    "ExpenseList",
    "ExpenseText",
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
    "payment_method_label",
]
