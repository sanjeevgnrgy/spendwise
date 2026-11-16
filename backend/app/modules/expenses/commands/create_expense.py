"""CreateExpense: record a new expense for one person. The command, the NewExpense it carries, and its handler.

A slice of the expenses module's write side. module.py registers the handler with the bus; callers send the
command (bus.execute(CreateExpense(...))) and never call the handler directly: POST /expenses (api.py, whose body
is NewExpense), MCP's add_expense and seed.py. The handler applies the business rules (domain/rules.py), then
stages the row through persistence/repository.py. The bus commits; the handler never does.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.core.money import DEFAULT_CURRENCY, CurrencyCode, rupees_to_paise
from app.modules.categories import CategoryId
from app.modules.expenses.domain.rules import require_category_exists, require_positive_amount
from app.modules.expenses.persistence import repository
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import Amount, Merchant, Note, PaymentMethod


# The new expense's fields, and the body of POST /expenses. Not a message: it has no owner, which the server adds
# from the session (CreateExpense), so a body can never name someone else (D190). Unknown fields are refused (a typo
# like "merchnat", or an "owner_id", is a 422); stray spaces are stripped ("Swiggy " would never match a filter).
class NewExpense(BaseModel):
    """A new expense. Also the body of POST /expenses."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    amount: Amount
    currency: CurrencyCode = DEFAULT_CURRENCY
    category_id: CategoryId
    merchant: Merchant
    note: Note | None = None
    spent_on: date
    payment_method: PaymentMethod


# Sent by POST /expenses, MCP's add_expense and seed.py. Beyond the shape NewExpense checks, the handler refuses an
# amount <= 0 or a category that doesn't exist, with a BusinessRuleError (create_expense, below).
class CreateExpense(Command[int]):
    """Record an expense for `owner_id`. Returns its id."""

    owner_id: UserId
    expense: NewExpense


def create_expense(ctx: Context, command: CreateExpense) -> int:
    """Record a new expense for the command's owner and return its id.

    Raises BusinessRuleError if the amount isn't above zero or the category doesn't exist (categories are shared by
    everyone). The amount arrives in rupees and is stored as whole paise; created_at comes from the app's clock (UTC).
    """
    new = command.expense
    require_positive_amount(new.amount)
    require_category_exists(ctx, new.category_id)
    # Every other field has the same name in NewExpense and the table, so they're copied across as is.
    fields = new.model_dump(exclude={"amount"})
    expense = Expense(
        owner_id=command.owner_id, amount_minor=rupees_to_paise(new.amount), created_at=ctx.clock.now(), **fields
    )
    return repository.add(ctx.session, expense)
