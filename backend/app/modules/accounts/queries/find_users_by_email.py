"""FindUsersByEmail: the ids of the people whose profile has this email. The query and its handler; it changes
nothing.

A slice of the accounts module's read side, for operator scripts only (backend/seed.py's --sample-for): no route
asks it, so it can't be used to find out who has an account. Never used to sign anyone in: people are found by
their identity, not their email (D187), and two accounts may share one, which is why it answers a list.
"""

from pydantic import Field
from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.modules.accounts.persistence.tables import AppUser
from app.modules.accounts.values import MAX_EMAIL_LENGTH


class FindUsersByEmail(Query[list[int]]):
    """The user ids whose email is this one (any letter case), oldest account first."""

    email: str = Field(min_length=1, max_length=MAX_EMAIL_LENGTH)


def find_users_by_email(ctx: Context, query: FindUsersByEmail) -> list[int]:
    """Every user id with that email, compared in lower case, oldest first."""
    statement = (
        select(AppUser.id).where(func.lower(AppUser.email) == query.email.strip().lower()).order_by(col(AppUser.id))
    )
    return [user_id for user_id in ctx.session.exec(statement) if user_id is not None]
