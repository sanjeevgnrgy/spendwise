"""How many rows a write statement touched (core layer).

Session.execute() is typed as returning a generic Result, but a DELETE or UPDATE returns a CursorResult, which knows
its rowcount. rows_affected says so once, for the repositories and handlers that need to know whether anything
matched (an owner's row not found is a NotFoundError, D190).
"""

from typing import Any, cast

from sqlalchemy import CursorResult, Executable
from sqlmodel import Session


def rows_affected(session: Session, statement: Executable) -> int:
    """Run a DELETE or UPDATE in `session` and return how many rows it touched."""
    return cast(CursorResult[Any], session.execute(statement)).rowcount
