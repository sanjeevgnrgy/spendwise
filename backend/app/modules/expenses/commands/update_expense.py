"""UpdateExpense: change some fields of one expense. The command, the ExpenseChanges it carries, and its handler.

A slice of the expenses module's write side. module.py registers the handler with the bus; the recorder
(application/record_expense.py, behind PATCH /expenses/{id}, whose body is ExpenseChanges, and MCP's update_expense)
sends the command, with the rate when the result is in another currency, and never calls the handler directly. The
handler applies the business rules (domain/rules.py, domain/base_amount.py) to what changed, then edits the row it
loads through persistence/repository.py. The bus commits; the handler never does.
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.core.money import CurrencyCode, rupees_to_paise
from app.modules.categories import CategoryId
from app.modules.expenses.conversion.port import ExchangeRate
from app.modules.expenses.domain.base_amount import base_amount_fields
from app.modules.expenses.domain.rules import require_category_exists, require_positive_amount
from app.modules.expenses.persistence import repository
from app.modules.expenses.values import Amount, ExpenseId, Merchant, Note, PaymentMethod

# The stored fields that decide the base amount: changing any of them converts the expense again (D204). The
# handler sees the table's names, so the amount is amount_minor.
CONVERTED_BY = frozenset({"amount_minor", "currency", "spent_on"})


# What to change in an expense: UpdateExpense carries it, and PATCH /expenses/{id} takes it as the body.
# Only a part of a command, not a Message itself, so it sets frozen and extra="forbid" on its own. Every
# field defaults to None, so the validator below tells "left out" apart from "sent as null".
class ExpenseChanges(BaseModel):
    """The body of PATCH /expenses/{id}: send only the fields you want to change."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    amount: Amount | None = None
    currency: CurrencyCode | None = None
    category_id: CategoryId | None = None
    merchant: Merchant | None = None
    spent_on: date | None = None
    payment_method: PaymentMethod | None = None
    # The one field that can be cleared: send "note": null to remove it.
    note: Note | None = None

    # Refuses null for any field but the note. The ValueError becomes a validation error that names the
    # fields (a 422 on REST). model_fields_set holds only the fields the caller actually sent, so fields
    # left out (None by default) pass.
    @model_validator(mode="after")
    def only_note_can_be_cleared(self) -> Self:
        # Leaving a field out means "don't change it"; sending null for it would mean "erase it",
        # which only makes sense for the note.
        cleared = sorted(name for name in self.model_fields_set if getattr(self, name) is None and name != "note")
        if cleared:
            raise ValueError(f"{', '.join(cleared)} can't be null; leave a field out to keep it as it is")
        return self


# Change some fields of one of the owner's expenses (PATCH /expenses/{id}, MCP's update_expense, through the
# recorder). The handler raises NotFoundError for a missing expense, or one that isn't the owner's (D190), and
# BusinessRuleError for an amount <= 0, an unknown category, or a change to the amount, currency or date of an
# expense in another currency without its `rate` (to INR, for the currency it ends up in); it raises the version by
# one. There's no expected_version: an update applies to whatever is stored (last write wins); only deletes check it.
class UpdateExpense(Command[None]):
    owner_id: UserId
    expense_id: ExpenseId
    changes: ExpenseChanges
    rate: ExchangeRate | None = None


def update_expense(ctx: Context, command: UpdateExpense) -> None:
    """Change the fields the caller sent and raise the expense's version by one.

    Raises NotFoundError if the owner has no such expense, and BusinessRuleError for an amount that isn't above zero, a
    category that doesn't exist, or a new amount, currency or date in another currency without its rate. Sending "note":
    null clears the note. The version isn't checked here: an update always applies to what's stored now.
    """
    expense = repository.get(ctx.session, command.owner_id, command.expense_id)
    # Only the fields the caller actually sent; anything left out stays as it was.
    changes = command.changes.model_dump(exclude_unset=True)
    if "amount" in changes:
        # Same rule and conversion as create_expense: rupees in, whole paise stored.
        amount = changes.pop("amount")
        require_positive_amount(amount)
        changes["amount_minor"] = rupees_to_paise(amount)
    if "category_id" in changes:
        require_category_exists(ctx, changes["category_id"])
    for field, value in changes.items():
        setattr(expense, field, value)
    # A new amount, currency or date means a new base amount (D204): worked out from what the expense is now.
    if CONVERTED_BY.intersection(changes):
        conversion = base_amount_fields(expense.amount_minor, expense.currency, expense.spent_on, command.rate)
        for field, value in conversion.items():
            setattr(expense, field, value)
    # Every update raises the version (even one with no changes, like an empty PATCH body), so a delete
    # that names the old one (DeleteExpense.expected_version) is refused instead of removing something the
    # user hasn't seen.
    expense.version += 1
