"""CreateExpense: record a new expense. The command and its handler.

A slice of the expenses module's write side. module.py registers the handler with the bus; callers send the
command (bus.execute(CreateExpense(...))) and never call the handler directly: POST /expenses (api.py, whose body
is this command), MCP's add_expense and seed.py. The handler applies the business rules (domain/rules.py), then
stages the row through persistence/repository.py. The bus commits; the handler never does.
"""

from datetime import date

from pydantic import ConfigDict

from app.core.cqrs import Command, Context
from app.core.money import DEFAULT_CURRENCY, CurrencyCode, rupees_to_paise
from app.modules.categories import CategoryId
from app.modules.expenses.domain.rules import require_category_exists, require_positive_amount
from app.modules.expenses.persistence import repository
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import Amount, Merchant, Note, PaymentMethod

# For bodies: strip stray spaces ("Swiggy " would never match a merchant filter). Unknown fields are
# already refused by every Command (a typo like "merchnat" is an error, not a silently ignored change).
_STRIPPED = ConfigDict(str_strip_whitespace=True)


# Sent by POST /expenses, MCP's add_expense and seed.py. Beyond the shape checked here, the handler
# refuses an amount <= 0 or a category that doesn't exist, with a BusinessRuleError
# (create_expense, below).
class CreateExpense(Command[int]):
    """Record an expense. Returns its id. Also the body of POST /expenses."""

    model_config = _STRIPPED

    amount: Amount
    currency: CurrencyCode = DEFAULT_CURRENCY
    category_id: CategoryId
    merchant: Merchant
    note: Note | None = None
    spent_on: date
    payment_method: PaymentMethod


def create_expense(ctx: Context, command: CreateExpense) -> int:
    """Record a new expense and return its id.

    Raises BusinessRuleError if the amount isn't above zero or the category doesn't exist. The amount
    arrives in rupees and is stored as whole paise; created_at comes from the app's clock (UTC).
    """
    require_positive_amount(command.amount)
    require_category_exists(ctx, command.category_id)
    # Every other field has the same name in the command and the table, so they're copied across as is.
    fields = command.model_dump(exclude={"amount"})
    expense = Expense(amount_minor=rupees_to_paise(command.amount), created_at=ctx.clock.now(), **fields)
    return repository.add(ctx.session, expense)
