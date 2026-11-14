"""Command handlers: the only code that changes expenses. The bus commits; handlers never do.

Part of the expenses module's write side. module.py registers each handler with the bus; callers send
the command (bus.execute(CreateExpense(...))) and never call a handler directly. Each handler applies the
business rules (domain.py, and the category check below), then stages its change through repository.py.
"""

from app.core.cqrs import Context
from app.core.errors import BusinessRuleError
from app.core.money import rupees_to_paise
from app.modules import categories
from app.modules.expenses import domain, repository
from app.modules.expenses.contracts import CreateExpense, DeleteExpense, UpdateExpense
from app.modules.expenses.tables import Expense


def _require_category(ctx: Context, category_id: int) -> None:
    """Raise BusinessRuleError unless the category exists.

    expense.category_id has no foreign key (each module owns its tables), so this check is what keeps
    an expense from pointing at a category that isn't there.
    """
    # Ask the categories module, through its contract, instead of reading its table.
    if ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")


def create_expense(ctx: Context, command: CreateExpense) -> int:
    """Record a new expense and return its id.

    Raises BusinessRuleError if the amount isn't above zero or the category doesn't exist. The amount
    arrives in rupees and is stored as whole paise; created_at comes from the app's clock (UTC).
    """
    domain.require_positive_amount(command.amount)
    _require_category(ctx, command.category_id)
    # Every other field has the same name in the command and the table, so they're copied across as is.
    fields = command.model_dump(exclude={"amount"})
    expense = Expense(amount_minor=rupees_to_paise(command.amount), created_at=ctx.clock.now(), **fields)
    return repository.add(ctx.session, expense)


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
        domain.require_positive_amount(amount)
        changes["amount_minor"] = rupees_to_paise(amount)
    if "category_id" in changes:
        _require_category(ctx, changes["category_id"])
    for field, value in changes.items():
        setattr(expense, field, value)
    # Every update raises the version (even one with no changes, like an empty PATCH body), so a delete
    # that names the old one (DeleteExpense.expected_version) is refused instead of removing something the
    # user hasn't seen.
    expense.version += 1


def delete_expense(ctx: Context, command: DeleteExpense) -> None:
    """Delete an expense; with expected_version, only if it's still at that version.

    Raises NotFoundError if it doesn't exist, and BusinessRuleError if it's at another version.
    """
    repository.remove(ctx.session, command.expense_id, command.expected_version)
