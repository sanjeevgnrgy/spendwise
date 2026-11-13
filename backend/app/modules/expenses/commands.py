"""Command handlers: the only code that changes expenses. The bus commits; handlers never do."""

from app.core.cqrs import Context
from app.core.errors import BusinessRuleError
from app.core.money import rupees_to_paise
from app.modules import categories
from app.modules.expenses import domain, repository
from app.modules.expenses.contracts import CreateExpense, DeleteExpense, UpdateExpense
from app.modules.expenses.tables import Expense


def _require_category(ctx: Context, category_id: int) -> None:
    # Ask the categories module, through its contract, instead of reading its table.
    if ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")


def create_expense(ctx: Context, command: CreateExpense) -> int:
    domain.require_positive_amount(command.amount)
    _require_category(ctx, command.category_id)
    fields = command.model_dump(exclude={"amount"})
    expense = Expense(amount_minor=rupees_to_paise(command.amount), created_at=ctx.clock.now(), **fields)
    return repository.add(ctx.session, expense)


def update_expense(ctx: Context, command: UpdateExpense) -> None:
    expense = repository.get(ctx.session, command.expense_id)
    # Only the fields the caller actually sent; anything left out stays as it was.
    changes = command.changes.model_dump(exclude_unset=True)
    if "amount" in changes:
        amount = changes.pop("amount")
        domain.require_positive_amount(amount)
        changes["amount_minor"] = rupees_to_paise(amount)
    if "category_id" in changes:
        _require_category(ctx, changes["category_id"])
    for field, value in changes.items():
        setattr(expense, field, value)
    expense.version += 1


def delete_expense(ctx: Context, command: DeleteExpense) -> None:
    repository.remove(ctx.session, command.expense_id, command.expected_version)
