"""The write side's access to the expenses table: load a row to change it, add one, remove one.

Changes are only staged in the session; the bus commits them when the command succeeds, so one
command's changes are saved together or not at all. Reads for display are the query slices (queries/).

Part of the expenses module, used only by its command handlers (the slices in commands/). Each function takes the
session from the handler's Context, so it works inside the command's unit of work.
"""

from sqlalchemy import delete
from sqlmodel import Session, col

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.i18n import translatable
from app.modules.expenses.i18n import ExpenseText
from app.modules.expenses.persistence.tables import Expense


def add(session: Session, expense: Expense) -> int:
    """Stage a new expense row and return the id the database gave it."""
    session.add(expense)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    session.flush()
    assert expense.id is not None
    return expense.id


def get(session: Session, expense_id: int) -> Expense:
    """Load an expense row to change it. Raises NotFoundError if there's no such expense.

    The row is tracked by the session: changing its attributes is enough, and the UPDATE is sent at the
    next flush (at the latest when the bus commits).
    """
    expense = session.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError(translatable(ExpenseText.NOT_FOUND, expense_id=expense_id))
    return expense


def remove(session: Session, expense_id: int, expected_version: int | None) -> None:
    """Delete the expense, and with `expected_version`, only if it's still at that version.

    One DELETE ... WHERE id = ? AND version = ?: the check and the delete are a single statement, so an
    edit that lands at the same moment can't be deleted unseen.

    Raises NotFoundError if the expense doesn't exist, and BusinessRuleError if it exists at another
    version (nothing is deleted then).
    """
    statement = delete(Expense).where(col(Expense.id) == expense_id)
    if expected_version is not None:
        statement = statement.where(col(Expense.version) == expected_version)
    # rowcount 0 means nothing matched: either there's no such expense, or (only with expected_version)
    # it's at another version. Looking it up tells the two apart, for a clear error.
    if session.execute(statement).rowcount == 0:
        current = get(session, expense_id)  # raises NotFoundError if it's gone
        raise BusinessRuleError(
            translatable(
                ExpenseText.CHANGED_SINCE_SHOWN,
                expense_id=expense_id,
                current=current.version,
                expected=expected_version,
            )
        )
