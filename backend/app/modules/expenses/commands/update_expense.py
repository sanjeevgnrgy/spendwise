"""UpdateExpense: change some fields of one expense. The command, the ExpenseChanges it carries, and its handler.

A slice of the expenses module's write side. module.py registers the handler with the bus; PATCH /expenses/{id}
(api.py, whose body is ExpenseChanges) and MCP's update_expense send the command and never call the handler
directly. The handler applies the business rules (domain/rules.py) to what changed, then edits the row it loads
through persistence/repository.py. The bus commits; the handler never does.
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.cqrs import Command, Context
from app.core.money import CurrencyCode, rupees_to_paise
from app.modules.categories import CategoryId
from app.modules.expenses.domain.rules import require_category_exists, require_positive_amount
from app.modules.expenses.persistence import repository
from app.modules.expenses.values import Amount, ExpenseId, Merchant, Note, PaymentMethod


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


# Change some fields of one expense (PATCH /expenses/{id}, MCP's update_expense). The handler raises
# NotFoundError for a missing expense and BusinessRuleError for an amount <= 0 or an unknown category,
# and raises the version by one. There's no expected_version: an update applies to whatever is stored
# (last write wins); only deletes check the version.
class UpdateExpense(Command[None]):
    expense_id: ExpenseId
    changes: ExpenseChanges


def update_expense(ctx: Context, command: UpdateExpense) -> None:
    """Change the fields the caller sent and raise the expense's version by one.

    Raises NotFoundError if there's no such expense, and BusinessRuleError for an amount that isn't above
    zero or a category that doesn't exist. Sending "note": null clears the note. The version isn't
    checked here: an update always applies to what's stored now.
    """
    expense = repository.get(ctx.session, command.expense_id)
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
    # Every update raises the version (even one with no changes, like an empty PATCH body), so a delete
    # that names the old one (DeleteExpense.expected_version) is refused instead of removing something the
    # user hasn't seen.
    expense.version += 1
