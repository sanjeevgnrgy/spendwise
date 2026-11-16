"""GetSession: the live session a cookie's key belongs to, if any. The query and its handler; it changes nothing.

A slice of the accounts module's read side. The session check (application/sessions.py) asks it on every request
to a protected route; module.py registers the handler. The rules for "live" are all in its one SELECT.
"""

from pydantic import Field
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.modules.accounts.models import SessionView
from app.modules.accounts.persistence.tables import AppUser, UserSession
from app.modules.accounts.queries.live_sessions import live_session_conditions
from app.modules.accounts.values import KEY_HASH_LENGTH, MAX_ISSUER_LENGTH


# Asked by SessionGate.authenticate with the hash of the cookie's key and the provider in use now.
class GetSession(Query[SessionView | None]):
    """The session, if it's live; None otherwise (unknown, signed out, expired, another provider's, user off)."""

    key_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)
    # The provider's issuer now; None when sign-in isn't configured, and then no session is live.
    issuer: str | None = Field(default=None, max_length=MAX_ISSUER_LENGTH)


def get_session(ctx: Context, query: GetSession) -> SessionView | None:
    """The session with that key, if it's live: not signed out, inside both expiries, signed in with today's
    provider (a switch of provider ends every older session), and its user switched on."""
    if query.issuer is None:
        return None
    statement = (
        select(UserSession)
        .join(AppUser, col(AppUser.id) == col(UserSession.user_id))
        .where(
            col(UserSession.key_hash) == query.key_hash,
            *live_session_conditions(ctx.clock.now(), query.issuer),
        )
    )
    session = ctx.session.exec(statement).first()
    if session is None or session.id is None:
        return None
    return SessionView(
        session_id=session.id, user_id=session.user_id, handle=session.handle, renewed_at=session.renewed_at
    )
