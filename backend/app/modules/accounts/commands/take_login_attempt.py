"""TakeLoginAttempt: read a sign-in attempt and forget it in one step, so each one completes once.

A slice of the accounts module's write side. The sign-in use case (application/sign_in.py) sends it when the
provider sends the browser back; module.py registers the handler.
"""

from pydantic import Field
from sqlmodel import select

from app.core.cqrs import Command, Context
from app.modules.accounts.models import LoginAttemptView
from app.modules.accounts.persistence.repository import forget_old_attempts
from app.modules.accounts.persistence.tables import LoginAttempt
from app.modules.accounts.values import KEY_HASH_LENGTH


# Sent by SignInFlow.finish with the hash of the login cookie's key.
class TakeLoginAttempt(Command[LoginAttemptView | None]):
    """The attempt, forgotten as it's returned; None if there's none (too old, already used, another browser's).

    A deliberate exception to "commands return at most an id", like TakeApproval: reading and removing must be one
    step, or a replayed callback could complete the same sign-in twice.
    """

    key_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)


def take_login_attempt(ctx: Context, command: TakeLoginAttempt) -> LoginAttemptView | None:
    """Return the attempt and delete it, in the same transaction. Expired attempts are forgotten first."""
    forget_old_attempts(ctx)
    attempt = ctx.session.exec(select(LoginAttempt).where(LoginAttempt.key_hash == command.key_hash)).first()
    if attempt is None:
        return None
    view = LoginAttemptView.model_validate(attempt)
    ctx.session.delete(attempt)
    return view
