"""Saving an expense, converted first when it isn't in INR: ExpenseRecorder.create and .update (D204).

A use case (application layer) of the expenses module, and its public way to create and change expenses: POST and
PATCH /expenses (api.py) and MCP's add_expense and update_expense use it. Not a handler: an amount in another
currency needs a rate from the currency agent, a network call that mustn't happen inside the bus's unit of work. So
the recorder asks ExchangeRates first, then sends CreateExpense or UpdateExpense with the rate; the handlers work out
and store the INR amount (domain/base_amount.py). Expenses in INR need no rate and no call.
"""

from dataclasses import dataclass
from datetime import date

from app.core.cqrs import MessageBus
from app.core.money import BASE_CURRENCY
from app.modules.expenses.commands.create_expense import CreateExpense, NewExpense
from app.modules.expenses.commands.update_expense import ExpenseChanges, UpdateExpense
from app.modules.expenses.conversion.port import ExchangeRate, ExchangeRates
from app.modules.expenses.queries.get_expense import GetExpense

# The fields of ExpenseChanges that decide the INR amount: an update touching one of them is converted again.
CONVERTED_BY = frozenset({"amount", "currency", "spent_on"})


@dataclass(frozen=True)
class ExpenseRecorder:
    """Creates and changes expenses, with a rate for any amount not in INR. Needs the bus and the rates."""

    bus: MessageBus
    rates: ExchangeRates

    def create(self, owner_id: int, new: NewExpense) -> int:
        """Record `new` for `owner_id` and return its id.

        Raises UnsupportedCurrencyError or RatesUnavailableError (from the rates) for an amount in another currency
        that can't be converted, and whatever CreateExpense raises (an amount <= 0, an unknown category).
        """
        rate = self._rate(new.currency, new.spent_on)
        return self.bus.execute(CreateExpense(owner_id=owner_id, expense=new, rate=rate))

    def update(self, owner_id: int, expense_id: int, changes: ExpenseChanges) -> None:
        """Apply `changes` to one of `owner_id`'s expenses, converting it again if its amount, currency or date
        changes into (or within) another currency.

        Raises NotFoundError for an expense they don't have, the rates' errors as for create, and whatever
        UpdateExpense raises.
        """
        rate = None
        if CONVERTED_BY.intersection(changes.model_fields_set):
            # What the expense will be once changed: the rate is for its currency, on its date.
            current = self.bus.ask(GetExpense(owner_id=owner_id, expense_id=expense_id))
            rate = self._rate(changes.currency or current.currency, changes.spent_on or current.spent_on)
        self.bus.execute(UpdateExpense(owner_id=owner_id, expense_id=expense_id, changes=changes, rate=rate))

    def _rate(self, currency: str, on: date) -> ExchangeRate | None:
        """The rate to INR for an amount in `currency` on `on`; None for INR, which needs none (and no call)."""
        return None if currency == BASE_CURRENCY else self.rates.to_base(currency, on)
