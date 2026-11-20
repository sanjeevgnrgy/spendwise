"""How the MCP tools show expenses and read category names: ExpenseView, with the category by name.

Part of the mcp adapter. Expenses keep only a category id (no foreign key: the categories table belongs
to the categories module), so the tools ask the categories module, through its contract and the bus, to
name it, and to turn a name a model sends into an id. The tools (tools/) and resources.py use this file;
server.py makes one ExpenseViews for them all.
"""

from app.core.cqrs import MessageBus
from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.modules import categories, expenses
from app.modules.mcp.contracts import ExpenseView


def to_view(expense: expenses.ExpenseRead, names: dict[int, str]) -> ExpenseView:
    """The expense as the tools show it: the category by name, the amount in rupees.

    `names` maps category ids to names. A category that isn't in it (it no longer exists) is shown as
    categories.UNKNOWN_CATEGORY, as the rest of the app does.
    """
    return ExpenseView(
        id=expense.id,
        amount=expense.amount,
        currency=expense.currency,
        amount_in_inr=expense.base_amount,
        category=names.get(expense.category_id, categories.UNKNOWN_CATEGORY),
        merchant=expense.merchant,
        note=expense.note,
        spent_on=expense.spent_on,
        payment_method=expense.payment_method,
        version=expense.version,
    )


class ExpenseViews:
    """Reads the tools share: category names and ids (shared by everyone), and one of a person's expenses as an
    ExpenseView.

    Each method sends queries through the bus, so each runs in its own unit of work.
    """

    def __init__(self, bus: MessageBus) -> None:
        """Keep the bus that every read goes through."""
        self._bus = bus

    def category_names(self) -> dict[int, str]:
        """Every category's name by id: one ListCategories, for naming a whole page of expenses at once."""
        return {c.id: c.name for c in self._bus.ask(categories.ListCategories())}

    def category_id(self, name: str) -> int:
        """The id of the category with this name, in any letter case and ignoring spaces around it.

        Raises BusinessRuleError if there's no such category: the message lists the categories that exist
        (so the model can pick one), or says there are none yet.
        """
        found = self._bus.ask(categories.FindCategoryByName(name=name))
        if found is not None:
            return found.id
        names = self.category_names().values()
        if not names:
            raise BusinessRuleError(translatable(categories.CategoryText.NO_CATEGORIES_YET))
        raise BusinessRuleError(f"Unknown category '{name.strip()}'. Use one of: {', '.join(names)}.")

    def find(self, owner_id: int, expense_id: int) -> ExpenseView:
        """One of `owner_id`'s expenses as an ExpenseView. Raises NotFoundError if they have no such expense.

        Names its category with one GetCategory (a primary-key lookup), not by loading every category.
        """
        expense = self._bus.ask(expenses.GetExpense(owner_id=owner_id, expense_id=expense_id))
        category = self._bus.ask(categories.GetCategory(category_id=expense.category_id))
        # A category that no longer exists gets no entry, so to_view shows it as UNKNOWN_CATEGORY.
        names = {category.id: category.name} if category is not None else {}
        return to_view(expense, names)
