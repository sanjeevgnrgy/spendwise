"""ListSessions: a person's live sessions (the browsers they're signed in on), most recently used first. The query
and its handler; it changes nothing.

A slice of the accounts module's read side, asked by GET /account/sessions (account_api.py) for the signed-in person.
"Live" means what the session check means (live_sessions.py), so the list shows exactly the sessions that still work.
"""

from pydantic import Field
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.modules.accounts.models import SessionRead
from app.modules.accounts.persistence.tables import AppUser, UserSession
from app.modules.accounts.queries.live_sessions import live_session_conditions
from app.modules.accounts.values import MAX_ISSUER_LENGTH


# Only the owner's sessions (D190). `issuer` is the provider in use now: sessions from an earlier one no longer work.
class ListSessions(Query[list[SessionRead]]):
    owner_id: UserId
    # None when sign-in isn't configured: then no session works, and the list is empty.
    issuer: str | None = Field(default=None, max_length=MAX_ISSUER_LENGTH)


def list_sessions(ctx: Context, query: ListSessions) -> list[SessionRead]:
    """The owner's live sessions, the most recently used first (`current` left False: the route knows which)."""
    if query.issuer is None:
        return []
    statement = (
        select(UserSession)
        .join(AppUser, col(AppUser.id) == col(UserSession.user_id))
        .where(col(UserSession.user_id) == query.owner_id, *live_session_conditions(ctx.clock.now(), query.issuer))
        .order_by(col(UserSession.renewed_at).desc(), col(UserSession.id).desc())
    )
    return [
        SessionRead(id=row.id, created_at=row.created_at, last_active_at=row.renewed_at, user_agent=row.user_agent)
        for row in ctx.session.exec(statement)
        if row.id is not None
    ]
