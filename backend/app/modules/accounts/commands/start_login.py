"""StartLogin: remember a sign-in that's leaving for the provider. The command and its handler.

A slice of the accounts module's write side. The sign-in use case (application/sign_in.py) sends it just before the
browser is redirected; the callback takes it back with TakeLoginAttempt. module.py registers the handler.
"""

from pydantic import Field

from app.core.cqrs import Command, Context
from app.modules.accounts.persistence.repository import forget_old_attempts
from app.modules.accounts.persistence.tables import LoginAttempt
from app.modules.accounts.values import KEY_HASH_LENGTH, MAX_STATE_LENGTH, MAX_URL_LENGTH, MAX_VERIFIER_LENGTH

# RFC 7636 (4.1): a PKCE verifier has at least 43 characters.
MIN_VERIFIER_LENGTH = 43


# Sent by SignInFlow.begin with the hash of the login cookie's key, and what the callback will check.
class StartLogin(Command[int]):
    """Returns the attempt's id."""

    key_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)
    state: str = Field(min_length=1, max_length=MAX_STATE_LENGTH)
    nonce: str = Field(min_length=1, max_length=MAX_STATE_LENGTH)
    code_verifier: str = Field(min_length=MIN_VERIFIER_LENGTH, max_length=MAX_VERIFIER_LENGTH)
    return_to: str = Field(min_length=1, max_length=MAX_URL_LENGTH)


def start_login(ctx: Context, command: StartLogin) -> int:
    """Store this attempt, stamped with the clock's now, then forget stale ones, keeping the newest
    MAX_LOGIN_ATTEMPTS (this one among them). Returns its id."""
    attempt = LoginAttempt(**command.model_dump(), created_at=ctx.clock.now())
    ctx.session.add(attempt)
    ctx.session.flush()
    assert attempt.id is not None
    forget_old_attempts(ctx)
    return attempt.id
