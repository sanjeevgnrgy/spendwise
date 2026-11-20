"""The rule for storing both amounts: every expense is also kept in the base currency, INR (D204).

A domain rule of the expenses module, applied by the CreateExpense and UpdateExpense handlers (commands/) whenever the
amount, the currency or the date is set. An expense in INR is its own base amount (rate 1, on its own date). Any other
currency needs the rate the recorder fetched before the command was sent (application/record_expense.py: no network
call inside a unit of work), for that same currency; the base amount is worked out here, with core.money's one
rounding rule, so it can never disagree with the rate stored beside it.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.core.money import BASE_CURRENCY, convert_minor
from app.modules.expenses.conversion.port import ExchangeRate
from app.modules.expenses.i18n import ExpenseText

# What an amount already in the base currency is multiplied by.
IDENTITY_RATE = Decimal(1)
# The fields of a row (and of persistence/tables.Expense) that this rule fills in.
CONVERSION_FIELDS = ("base_amount_minor", "exchange_rate", "rate_date")


def base_amount_fields(amount_minor: int, currency: str, spent_on: date, rate: ExchangeRate | None) -> dict[str, Any]:
    """The base-currency fields for an amount: the INR amount in paise, the rate (as text, exactly) and its date.

    Raises BusinessRuleError if the currency isn't INR and `rate` is missing or for another currency (the expense
    changed between the recorder's lookup and the command: saving it again fetches the right rate).
    """
    if currency == BASE_CURRENCY:
        return dict(zip(CONVERSION_FIELDS, (amount_minor, str(IDENTITY_RATE), spent_on), strict=True))
    if rate is None or rate.currency != currency:
        raise BusinessRuleError(translatable(ExpenseText.RATE_MISSING, currency=currency))
    converted = convert_minor(amount_minor, rate.rate)
    return dict(zip(CONVERSION_FIELDS, (converted, str(rate.rate), rate.rate_date), strict=True))
