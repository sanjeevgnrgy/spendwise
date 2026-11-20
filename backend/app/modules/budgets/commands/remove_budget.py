"""RemoveBudget: remove one of a person's monthly budgets. The command and its handler.

A slice of the budgets module's write side. module.py registers the handler with the bus; callers send the command:
DELETE /budgets/overall and DELETE /budgets/categories/{id} (api.py), and in part 2 the assistant's tool. The bus
commits; the handler never does.
"""

from app.core.cqrs import Command, Context
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.modules import categories
from app.modules.budgets.i18n import BudgetText
from app.modules.budgets.persistence import repository


# category_id None means the overall budget. Removing a budget the owner doesn't have is a NotFoundError.
class RemoveBudget(Command[None]):
    """Remove `owner_id`'s monthly budget for a category, or the overall one."""

    owner_id: UserId
    category_id: categories.CategoryId | None = None


def remove_budget(ctx: Context, command: RemoveBudget) -> None:
    """Delete the owner's budget for the command's scope. Raises NotFoundError if they have none (another person's
    budget is never touched: the statement names the owner)."""
    if not repository.remove(ctx.session, command.owner_id, command.category_id):
        if command.category_id is None:
            raise NotFoundError(translatable(BudgetText.NO_OVERALL_BUDGET))
        raise NotFoundError(translatable(BudgetText.NO_CATEGORY_BUDGET, category_id=command.category_id))
