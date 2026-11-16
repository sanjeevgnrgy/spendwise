"""GetExpense: one of a person's expenses by id. The query and its handler; it never changes anything.

A slice of the expenses module's read side. module.py registers the handler with the bus. Routes ask it after a
command to answer with the saved expense (api.py), and the MCP tools to show one. The answer is a frozen
ExpenseRead (models.py), never a table row.
"""

from sqlmodel import select

from app.core.cqrs import Context, Query
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.modules.expenses.i18n import ExpenseText
from app.modules.expenses.models import ExpenseRead
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import ExpenseId


# Routes ask it after a command to answer with the saved expense; the MCP tools ask it to show one.
class GetExpense(Query[ExpenseRead]):
    """One of the owner's expenses. Raises NotFoundError if they have no such expense."""

    owner_id: UserId
    expense_id: ExpenseId


def get_expense(ctx: Context, query: GetExpense) -> ExpenseRead:
    """One of the owner's expenses by id. Raises NotFoundError if they have no such expense.

    The owner and the id are matched in the same statement: another person's expense is "not found", like one that
    doesn't exist, so its existence isn't revealed either (D190).
    """
    statement = select(Expense).where(Expense.id == query.expense_id, Expense.owner_id == query.owner_id)
    row = ctx.session.exec(statement).first()
    if row is None:
        raise NotFoundError(translatable(ExpenseText.NOT_FOUND, expense_id=query.expense_id))
    return ExpenseRead.model_validate(row)
