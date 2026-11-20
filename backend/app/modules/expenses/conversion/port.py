"""The expenses module's exchange-rate port: what saving an expense in another currency needs, whoever provides it.

Port. The recorder (application/record_expense.py) asks ExchangeRates for the rate to the base currency (INR) on the
expense's date, and sends it with CreateExpense or UpdateExpense, whose handlers store both amounts (D204). The
composition root decides what's behind it, through module.py: currency_agent.CurrencyAgentRates, the currency agent
(agents/currency) through the remote-agents port. A check passes a fake.
"""

from datetime import date
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import BusinessRuleError, ExternalServiceError
from app.core.money import CurrencyCode


class RatesUnavailableError(ExternalServiceError):
    """No rate could be had (the currency agent isn't configured, can't be reached, or answered something unusable),
    so an amount in another currency can't be saved now (the owner's choice: refuse rather than save it half-done)."""


class UnsupportedCurrencyError(BusinessRuleError):
    """The rates provider has no rate for this currency: the expense can't be saved in it."""


# A rate to the base currency, as the handlers receive it inside a command: what 1 unit of `currency` was worth in
# INR on `rate_date`. Part of CreateExpense and UpdateExpense, so frozen and checked like any message field.
class ExchangeRate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    currency: CurrencyCode
    rate: Decimal = Field(gt=0)
    rate_date: date


class ExchangeRates(Protocol):
    """Where rates to the base currency come from."""

    def to_base(self, currency: str, on: date) -> ExchangeRate:
        """What 1 unit of `currency` is worth in the base currency on `on` (or the nearest earlier day it has).

        Raises UnsupportedCurrencyError for a currency it can't convert, RatesUnavailableError if it can't answer.
        """
        ...
