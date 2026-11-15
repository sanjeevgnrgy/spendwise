"""The accounts module's tables: people, how they sign in, their sessions, and sign-ins under way.

Private to this module: only its own handlers (the slices in commands/ and queries/, through repository.py) read or
write them. The foreign keys stay inside the module (D13 forbids them only between modules). Created and changed by
Alembic migrations, never by the app.
"""

from datetime import datetime

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.modules.accounts.values import (
    HANDLE_LENGTH,
    KEY_HASH_LENGTH,
    MAX_EMAIL_LENGTH,
    MAX_ISSUER_LENGTH,
    MAX_NAME_LENGTH,
    MAX_STATE_LENGTH,
    MAX_SUBJECT_LENGTH,
    MAX_URL_LENGTH,
    MAX_VERIFIER_LENGTH,
)


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class AppUser(SQLModel, table=True):
    """A person who uses SpendWise. Private to the accounts module."""

    # Not "user": that's a reserved word in Postgres.
    __tablename__ = "app_user"

    # SpendWise's own id for the person: what everything else points at, whatever provider they sign in with.
    id: int | None = Field(default=None, primary_key=True)
    # The profile as the provider last said, refreshed at each sign-in. Shown, never used to find the person.
    name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    email: str | None = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    email_verified: bool = False
    avatar_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    # SpendWise's own off switch: a person switched off can't sign in, and their sessions stop working.
    is_active: bool = True
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True))


class UserIdentity(SQLModel, table=True):
    """One way a person signs in: a provider (issuer) and their id there (subject). Private to the accounts module."""

    __tablename__ = "user_identity"
    # One person per identity: the same provider account can never become two users.
    __table_args__ = (UniqueConstraint("issuer", "subject"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="app_user.id", index=True)
    issuer: str = Field(max_length=MAX_ISSUER_LENGTH)
    subject: str = Field(max_length=MAX_SUBJECT_LENGTH)
    # The email the provider gave when this identity was first seen: a record, never a way to match people.
    email: str | None = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    created_at: datetime = Field(sa_type=DateTime(timezone=True))


class UserSession(SQLModel, table=True):
    """A signed-in browser. Its cookie holds a random key; only the key's hash is stored. Private to accounts."""

    __tablename__ = "user_session"

    id: int | None = Field(default=None, primary_key=True)
    # SHA-256 of the cookie's key: a copy of the database can't be turned back into a working cookie.
    key_hash: str = Field(max_length=KEY_HASH_LENGTH, unique=True)
    # A random public name for the session: the sign-out link carries it, so another site can't sign anyone out.
    handle: str = Field(max_length=HANDLE_LENGTH, unique=True)
    user_id: int = Field(foreign_key="app_user.id", index=True)
    # The provider it was signed in with: after a switch of provider, its sessions are no longer accepted.
    issuer: str = Field(max_length=MAX_ISSUER_LENGTH)
    # The provider's own session (OIDC `sid`), to end this one when the provider says that one ended.
    provider_session_id: str | None = Field(default=None, max_length=MAX_SUBJECT_LENGTH, index=True)
    # The ID token, sealed (core/sealing.py): signing out names it to the provider.
    sealed_id_token: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
    renewed_at: datetime = Field(sa_type=DateTime(timezone=True))
    # Ends when unused this long (renewed while used)...
    expires_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    # ...and at this moment at the latest.
    absolute_expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    # Set when it's signed out or revoked; kept until it would have expired anyway.
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class LoginAttempt(SQLModel, table=True):
    """A sign-in under way at the provider: what the callback must check. Used once. Private to accounts."""

    __tablename__ = "login_attempt"

    id: int | None = Field(default=None, primary_key=True)
    # SHA-256 of the short-lived login cookie's key: the attempt only completes in the browser that started it.
    key_hash: str = Field(max_length=KEY_HASH_LENGTH, unique=True)
    state: str = Field(max_length=MAX_STATE_LENGTH)
    nonce: str = Field(max_length=MAX_STATE_LENGTH)
    code_verifier: str = Field(max_length=MAX_VERIFIER_LENGTH)
    # The page to come back to: a path in the web app, already checked (domain/return_paths.py).
    return_to: str = Field(max_length=MAX_URL_LENGTH)
    created_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (AppUser, UserIdentity, UserSession, LoginAttempt)
