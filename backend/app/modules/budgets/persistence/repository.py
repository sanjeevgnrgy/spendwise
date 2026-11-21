"""The write side's access to the budget table: find a person's budget for a scope, save one, remove one.

Changes are only staged in the session; the bus commits them when the command succeeds. Every statement names the
owner (D190): another person's budget is never found or changed. Part of the budgets module, used only by its command
handlers (commands/), with the session from the handler's Context.
"""

from sqlalchemy import ColumnElement, delete
from sqlmodel import Session, col, select

from app.core.sql import rows_affected
from app.modules.budgets.persistence.tables import Budget


def _scope(category_id: int | None) -> ColumnElement[bool]:
    """The condition for one scope: that category, or the overall budget (no category)."""
    return col(Budget.category_id).is_(None) if category_id is None else col(Budget.category_id) == category_id


def find(session: Session, owner_id: int, category_id: int | None) -> Budget | None:
    """`owner_id`'s budget for the category (None: the overall budget), or None if they haven't set one."""
    statement = select(Budget).where(col(Budget.owner_id) == owner_id, _scope(category_id))
    return session.exec(statement).first()


def save(session: Session, budget: Budget) -> int:
    """Stage a new or changed budget and return its id (flushed, so a new row has one)."""
    session.add(budget)
    session.flush()
    assert budget.id is not None
    return budget.id


def remove(session: Session, owner_id: int, category_id: int | None) -> bool:
    """Delete `owner_id`'s budget for the scope, in one statement that names the owner. True if there was one."""
    statement = delete(Budget).where(col(Budget.owner_id) == owner_id, _scope(category_id))
    return rows_affected(session, statement) > 0
