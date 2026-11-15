"""RevokeSessions: end the sessions a provider says have ended there (back-channel logout). Command and handler.

A slice of the accounts module's write side. The sign-out use case (application/sign_out.py) sends it once the
provider's logout token has passed every check; module.py registers the handler.
"""

from pydantic import Field
from sqlmodel import col, select, update

from app.core.cqrs import Command, Context
from app.modules.accounts.persistence.tables import UserIdentity, UserSession
from app.modules.accounts.values import MAX_ISSUER_LENGTH, MAX_SUBJECT_LENGTH


# Sent by SignOutFlow.back_channel with what the logout token names: a provider session (sid), a user (sub), or both.
class RevokeSessions(Command[None]):
    """Ends the sessions from `issuer` for that provider session; with no session named, all of that user's."""

    issuer: str = Field(min_length=1, max_length=MAX_ISSUER_LENGTH)
    subject: str | None = Field(default=None, max_length=MAX_SUBJECT_LENGTH)
    provider_session_id: str | None = Field(default=None, max_length=MAX_SUBJECT_LENGTH)


def revoke_sessions(ctx: Context, command: RevokeSessions) -> None:
    """Set revoked_at on the live sessions the notice names (Back-Channel Logout 1.0, 2.7): the provider session's
    if it names one, else every session of the user it names. Nothing happens if neither matches."""
    which = [col(UserSession.issuer) == command.issuer, col(UserSession.revoked_at).is_(None)]
    if command.provider_session_id is not None:
        which.append(col(UserSession.provider_session_id) == command.provider_session_id)
    elif command.subject is not None:
        user = select(UserIdentity.user_id).where(
            UserIdentity.issuer == command.issuer, UserIdentity.subject == command.subject
        )
        which.append(col(UserSession.user_id).in_(user))
    else:
        return
    ctx.session.execute(update(UserSession).where(*which).values(revoked_at=ctx.clock.now()))
