"""SignOutOtherSessions: end every session of a person's but the one they're using. The command and its handler.

A slice of the accounts module's write side, sent by POST /account/sessions/sign-out-others (account_api.py) for the
signed-in person, keeping the session the request came from. Only the owner's sessions are touched (D190); their
cookies stop working at once.
"""

from sqlalchemy import update
from sqlmodel import col

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import SessionId


# Keeps `keep_session_id` (the browser asking) and ends every other session of the owner's.
class SignOutOtherSessions(Command[None]):
    owner_id: UserId
    keep_session_id: SessionId


def sign_out_other_sessions(ctx: Context, command: SignOutOtherSessions) -> None:
    """Revoke every session of the owner's that isn't signed out yet, except the one to keep."""
    statement = (
        update(UserSession)
        .where(
            col(UserSession.user_id) == command.owner_id,
            col(UserSession.id) != command.keep_session_id,
            col(UserSession.revoked_at).is_(None),
        )
        .values(revoked_at=ctx.clock.now())
    )
    ctx.session.execute(statement)
