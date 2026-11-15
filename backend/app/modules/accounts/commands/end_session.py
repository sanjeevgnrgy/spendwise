"""EndSession: sign one session out, now. The command and its handler.

A slice of the accounts module's write side. Sent by the sign-out use case (application/sign_out.py) when a person
signs out, and by the sign-in use case to end the session a browser had before signing in again (a new session is
always started, never an old one reused). module.py registers the handler.
"""

from typing import Self

from pydantic import Field, model_validator
from sqlmodel import col, update

from app.core.cqrs import Command, Context
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import KEY_HASH_LENGTH, SessionId


# Sent with the session's id (sign-out) or the hash of its cookie's key (a new sign-in in the same browser).
class EndSession(Command[None]):
    """Marks the session revoked; it's no longer accepted. Nothing happens if it's unknown or already ended."""

    session_id: SessionId | None = None
    key_hash: str | None = Field(default=None, min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        """Exactly one of session_id and key_hash names the session. Raises ValueError otherwise."""
        if (self.session_id is None) == (self.key_hash is None):
            raise ValueError("EndSession takes a session_id or a key_hash, not both")
        return self


def end_session(ctx: Context, command: EndSession) -> None:
    """Set revoked_at to the clock's now on the session, if it's still live."""
    which = (
        col(UserSession.id) == command.session_id
        if command.session_id is not None
        else col(UserSession.key_hash) == command.key_hash
    )
    still_live = col(UserSession.revoked_at).is_(None)
    ctx.session.execute(update(UserSession).where(which, still_live).values(revoked_at=ctx.clock.now()))
