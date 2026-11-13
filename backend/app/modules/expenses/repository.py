"""The write side's access to the expenses table: load a row to change it, add one, remove one.

Changes are only staged in the session; the bus commits them when the command succeeds, so one
command's changes are saved together or not at all. Reads for display are queries (queries.py).
"""

from sqlalchemy import delete
from sqlmodel import Session, col

from app.core.errors import BusinessRuleError, NotFoundError
from app.modules.expenses.tables import Expense


def add(session: Session, expense: Expense) -> int:
    session.add(expense)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    session.flush()
    assert expense.id is not None
    return expense.id


def get(session: Session, expense_id: int) -> Expense:
    expense = session.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError(f"Expense {expense_id} not found")
    return expense


def remove(session: Session, expense_id: int, expected_version: int | None) -> None:
    """Delete the expense, and with `expected_version`, only if it's still at that version.

    One DELETE ... WHERE id = ? AND version = ?: the check and the delete are a single statement, so an
    edit that lands at the same moment can't be deleted unseen.
    """
    statement = delete(Expense).where(col(Expense.id) == expense_id)
    if expected_version is not None:
        statement = statement.where(col(Expense.version) == expected_version)
    if session.execute(statement).rowcount == 0:
        current = get(session, expense_id)  # raises NotFoundError if it's gone
        raise BusinessRuleError(
            f"Expense {expense_id} has changed since it was shown (version {current.version}, not "
            f"{expected_version}); nothing was deleted."
        )
