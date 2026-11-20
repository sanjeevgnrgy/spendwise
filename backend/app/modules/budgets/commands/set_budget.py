"""SetBudget: set one of a person's monthly budgets (overall, or for a category). The command, its body and handler.

A slice of the budgets module's write side. module.py registers the handler with the bus; callers send the command:
PUT /budgets/overall and PUT /budgets/categories/{id} (api.py), and in Phase 27 part 2 the assistant's tool. Setting a
budget that exists changes its limit; otherwise one is created. The bus commits; the handler never does.
"""

from pydantic import BaseModel, ConfigDict

from app.core.cqrs import Command, Context
from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.core.money import rupees_to_paise
from app.modules import categories
from app.modules.budgets.i18n import BudgetText
from app.modules.budgets.persistence import repository
from app.modules.budgets.persistence.tables import Budget
from app.modules.budgets.values import BudgetLimit


# The body of the PUT routes: the new monthly limit, in rupees. Not a message: it has no owner (the server adds it,
# D190), and unknown fields are refused.
class BudgetChange(BaseModel):
    """A monthly limit, in rupees."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    limit: BudgetLimit


# Sent by the PUT routes (and, in part 2, the assistant). category_id None means the overall budget. A category that
# doesn't exist is a BusinessRuleError (set_budget, below).
class SetBudget(Command[int]):
    """Set `owner_id`'s monthly budget for a category, or the overall one. Returns the budget's id."""

    owner_id: UserId
    category_id: categories.CategoryId | None = None
    limit: BudgetLimit


def set_budget(ctx: Context, command: SetBudget) -> int:
    """Create or change the owner's budget for the command's scope, and return its id. The limit is stored in paise;
    updated_at comes from the app's clock. Raises BusinessRuleError for a category that doesn't exist."""
    category_id = command.category_id
    # budget.category_id has no foreign key (each module owns its tables): this check keeps it pointing at a category.
    if category_id is not None and ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(translatable(BudgetText.CATEGORY_MISSING, category_id=category_id))
    limit_minor = rupees_to_paise(command.limit)
    budget = repository.find(ctx.session, command.owner_id, category_id)
    if budget is None:
        budget = Budget(owner_id=command.owner_id, category_id=category_id, limit_minor=limit_minor,
                        updated_at=ctx.clock.now())
    else:
        budget.limit_minor = limit_minor
        budget.updated_at = ctx.clock.now()
    return repository.save(ctx.session, budget)
