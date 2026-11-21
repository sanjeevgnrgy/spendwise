"""SignOutSession: end one of a person's sessions (a browser left signed in elsewhere). The command and its handler.

A slice of the accounts module's write side, sent by DELETE /account/sessions/{id} (account_api.py) for the signed-in
person. The statement names the owner: nobody can end another person's session, or learn that it exists (D190).
The session's cookie stops working at once (the session check finds it revoked). The provider's own session isn't
touched: the person signs out there through the provider, or the next sign-in asks again.
"""

from sqlalchemy import update
from sqlmodel import col

from app.core.cqrs import Command, Context
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.core.sql import rows_affected
from app.modules.accounts.i18n import AccountText
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import SessionId


# Raises NotFoundError if the owner has no such session still signed in (another person's counts as none).
class SignOutSession(Command[None]):
    owner_id: UserId
    session_id: SessionId


def sign_out_session(ctx: Context, command: SignOutSession) -> None:
    """Revoke the owner's session. Raises NotFoundError if they have no such session that isn't signed out yet."""
    statement = (
        update(UserSession)
        .where(
            col(UserSession.id) == command.session_id,
            col(UserSession.user_id) == command.owner_id,
            col(UserSession.revoked_at).is_(None),
        )
        .values(revoked_at=ctx.clock.now())
    )
    if rows_affected(ctx.session, statement) == 0:
        raise NotFoundError(translatable(AccountText.SESSION_NOT_FOUND, session_id=command.session_id))
