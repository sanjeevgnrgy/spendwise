"""SignIn: turn a verified sign-in into a user (found or new) and a new session. The command and its handler.

A slice of the accounts module's write side. The sign-in use case (application/sign_in.py) sends it once every check
on the provider's answer has passed; module.py registers the handler. The bus commits; the handler never does.
"""

from pydantic import Field

from app.core.cqrs import Command, Context
from app.modules.accounts.domain.rules import AccountDisabledError, Profile
from app.modules.accounts.persistence.repository import add_user, find_user_id, forget_ended_sessions, refresh_profile
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import (
    HANDLE_LENGTH,
    KEY_HASH_LENGTH,
    MAX_EMAIL_LENGTH,
    MAX_ISSUER_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SUBJECT_LENGTH,
    MAX_URL_LENGTH,
    MAX_USER_AGENT_LENGTH,
    SESSION_IDLE,
    SESSION_LIFETIME,
)


# Sent by SignInFlow.finish: who signed in (issuer and subject), their profile, and the new session's stored values.
class SignIn(Command[int]):
    """Returns the new session's id. Raises AccountDisabledError if the user is switched off."""

    issuer: str = Field(min_length=1, max_length=MAX_ISSUER_LENGTH)
    subject: str = Field(min_length=1, max_length=MAX_SUBJECT_LENGTH)
    name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    email: str | None = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    email_verified: bool = False
    avatar_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    key_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)
    handle: str = Field(min_length=HANDLE_LENGTH, max_length=HANDLE_LENGTH)
    provider_session_id: str | None = Field(default=None, max_length=MAX_SUBJECT_LENGTH)
    sealed_id_token: str | None = None
    user_agent: str | None = Field(default=None, max_length=MAX_USER_AGENT_LENGTH)


def sign_in(ctx: Context, command: SignIn) -> int:
    """Find the user by issuer and subject, or add them, refresh their profile, and start a session.

    A person is found only by the identity they signed in with, never by email: two provider accounts with the same
    email are two users (D187). Raises AccountDisabledError (and changes nothing) if the user is switched off.
    """
    profile = Profile(
        name=command.name, email=command.email, email_verified=command.email_verified, avatar_url=command.avatar_url
    )
    user_id = find_user_id(ctx, command.issuer, command.subject)
    if user_id is None:
        user_id = add_user(ctx, profile, command.issuer, command.subject)
    if not refresh_profile(ctx, user_id, profile).is_active:
        raise AccountDisabledError(f"user {user_id} is switched off")
    forget_ended_sessions(ctx)
    now = ctx.clock.now()
    session = UserSession(
        key_hash=command.key_hash,
        handle=command.handle,
        user_id=user_id,
        issuer=command.issuer,
        provider_session_id=command.provider_session_id,
        sealed_id_token=command.sealed_id_token,
        user_agent=command.user_agent,
        created_at=now,
        renewed_at=now,
        expires_at=now + SESSION_IDLE,
        absolute_expires_at=now + SESSION_LIFETIME,
    )
    ctx.session.add(session)
    ctx.session.flush()
    assert session.id is not None
    return session.id
