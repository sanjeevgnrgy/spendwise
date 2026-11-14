"""GetExpense: one expense by id. The query and its handler; it never changes anything.

A slice of the expenses module's read side. module.py registers the handler with the bus. Routes ask it after a
command to answer with the saved expense (api.py), and the MCP tools to show one. The answer is a frozen
ExpenseRead (models.py), never a table row.
"""

from app.core.cqrs import Context, Query
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.modules.expenses.i18n import ExpenseText
from app.modules.expenses.models import ExpenseRead
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import ExpenseId


# Routes ask it after a command to answer with the saved expense; the MCP tools ask it to show one.
class GetExpense(Query[ExpenseRead]):
    """One expense. Raises NotFoundError if there's no such expense."""

    expense_id: ExpenseId


def get_expense(ctx: Context, query: GetExpense) -> ExpenseRead:
    """One expense by id. Raises NotFoundError if there's no such expense."""
    row = ctx.session.get(Expense, query.expense_id)
    if row is None:
        raise NotFoundError(translatable(ExpenseText.NOT_FOUND, expense_id=query.expense_id))
    return ExpenseRead.model_validate(row)
