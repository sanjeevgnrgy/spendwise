"""Expenses module: money spent, with amount, category, merchant and date.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.expenses`, and send them through the bus. Tables, handlers, the repository and the router
stay private; the composition root (bootstrap.py) plugs them in through module.py.

Inside, each command and each query is one file holding the message, its handler and anything only it uses
(commands/, queries/). What several of them share: values.py (limits, PaymentMethod, field types), models.py
(ExpenseRead, ExpenseList, the totals' base), domain/rules.py (business rules) and persistence/ (the table and
the write side's repository). This file only re-exports the contract names from those files.

Every command and query about expenses names its owner (`owner_id`, a core.ids.UserId): one person's expenses are
never visible to, or changeable by, anyone else (D190).

Saving goes through ExpenseRecorder (application/record_expense.py), which converts an amount in another currency
to INR first, through the ExchangeRates port (conversion/; the currency agent behind it, D204); every expense keeps
both amounts.

Who uses it: the MCP server (the recorder for its add and update tools, the commands and queries behind the others),
the assistant (PaymentMethod and payment_method_label for its forms, MAX_NOTE_LENGTH for a receipt's note) and
seed.py (CreateExpense, in INR, and ListExpenses), and the reports module (ListExpenses for a month's report,
MAX_MERCHANT_LENGTH to check the report's figures, payment_method_label for its downloads).
"""

from app.modules.expenses.application.record_expense import ExpenseRecorder
from app.modules.expenses.commands.create_expense import CreateExpense, NewExpense
from app.modules.expenses.commands.delete_expense import DeleteExpense
from app.modules.expenses.commands.update_expense import ExpenseChanges, UpdateExpense
from app.modules.expenses.conversion.port import (
    ExchangeRate,
    ExchangeRates,
    RatesUnavailableError,
    UnsupportedCurrencyError,
)
from app.modules.expenses.i18n import ExpenseText, payment_method_label
from app.modules.expenses.models import ExpenseList, ExpenseRead
from app.modules.expenses.queries.get_expense import GetExpense
from app.modules.expenses.queries.get_monthly_summary import CategoryTotal, GetMonthlySummary, MonthlySummary
from app.modules.expenses.queries.get_monthly_trend import GetMonthlyTrend, MonthlyTrend, MonthTotal
from app.modules.expenses.queries.list_expenses import ExpenseFilters, ListExpenses
from app.modules.expenses.values import MAX_LIST_LIMIT, MAX_MERCHANT_LENGTH, MAX_NOTE_LENGTH, ExpenseId, PaymentMethod

__all__ = [
    "MAX_LIST_LIMIT",
    "MAX_MERCHANT_LENGTH",
    "MAX_NOTE_LENGTH",
    "CategoryTotal",
    "CreateExpense",
    "DeleteExpense",
    "ExchangeRate",
    "ExchangeRates",
    "ExpenseChanges",
    "ExpenseFilters",
    "ExpenseId",
    "ExpenseList",
    "ExpenseText",
    "ExpenseRead",
    "ExpenseRecorder",
    "GetExpense",
    "GetMonthlySummary",
    "GetMonthlyTrend",
    "ListExpenses",
    "MonthTotal",
    "MonthlySummary",
    "MonthlyTrend",
    "NewExpense",
    "PaymentMethod",
    "RatesUnavailableError",
    "UnsupportedCurrencyError",
    "UpdateExpense",
    "payment_method_label",
]
