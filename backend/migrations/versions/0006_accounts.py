"""Accounts get their tables: people, how they sign in, their sessions, and sign-ins under way (Phase 22).

- app_user: a person, SpendWise's own id for them, and their profile as the provider last said.
- user_identity: how a person signs in, a provider (issuer) and their id there (subject), unique together.
- user_session: a signed-in browser. Only the SHA-256 of its cookie's key is stored, with the provider's ID token
  sealed (encrypted), the provider's session id, and when it was renewed, expires and was revoked.
- login_attempt: a sign-in that has left for the provider (state, nonce, PKCE verifier), used once.

New tables, so existing data is untouched; downgrade drops them, which signs everyone out and forgets who they were
(nothing else points at them yet).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app (accounts/values.py has the same sizes): a migration must keep doing
# exactly what it did, even after the app's code changes.
KEY_HASH_LENGTH = 64
HANDLE_LENGTH = 32
ISSUER_LENGTH = 255
SUBJECT_LENGTH = 255
EMAIL_LENGTH = 320
NAME_LENGTH = 200
URL_LENGTH = 2048
STATE_LENGTH = 64
VERIFIER_LENGTH = 128


def _moment(name: str, nullable: bool = False) -> sa.Column:
    """A timestamp column, stored with its time zone (the app writes UTC)."""
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _create_app_user() -> None:
    """app_user: a person and their profile."""
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=NAME_LENGTH), nullable=True),
        sa.Column("email", sa.String(length=EMAIL_LENGTH), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("avatar_url", sa.String(length=URL_LENGTH), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _moment("created_at"),
        _moment("updated_at"),
    )


def _create_user_identity() -> None:
    """user_identity: how a person signs in (issuer and subject, unique together)."""
    op.create_table(
        "user_identity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("issuer", sa.String(length=ISSUER_LENGTH), nullable=False),
        sa.Column("subject", sa.String(length=SUBJECT_LENGTH), nullable=False),
        sa.Column("email", sa.String(length=EMAIL_LENGTH), nullable=True),
        _moment("created_at"),
        # One person per identity. Unnamed, as the table class declares it, so the database and the model agree.
        sa.UniqueConstraint("issuer", "subject"),
    )
    op.create_index("ix_user_identity_user_id", "user_identity", ["user_id"])


def _create_user_session() -> None:
    """user_session: a signed-in browser (only its key's hash), and its indexes."""
    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(length=KEY_HASH_LENGTH), nullable=False),
        sa.Column("handle", sa.String(length=HANDLE_LENGTH), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("issuer", sa.String(length=ISSUER_LENGTH), nullable=False),
        sa.Column("provider_session_id", sa.String(length=SUBJECT_LENGTH), nullable=True),
        sa.Column("sealed_id_token", sa.Text(), nullable=True),
        _moment("created_at"),
        _moment("renewed_at"),
        _moment("expires_at"),
        _moment("absolute_expires_at"),
        _moment("revoked_at", nullable=True),
        sa.UniqueConstraint("key_hash"),
        sa.UniqueConstraint("handle"),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])
    op.create_index("ix_user_session_provider_session_id", "user_session", ["provider_session_id"])
    op.create_index("ix_user_session_expires_at", "user_session", ["expires_at"])


def _create_login_attempt() -> None:
    """login_attempt: a sign-in under way, used once."""
    op.create_table(
        "login_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(length=KEY_HASH_LENGTH), nullable=False),
        sa.Column("state", sa.String(length=STATE_LENGTH), nullable=False),
        sa.Column("nonce", sa.String(length=STATE_LENGTH), nullable=False),
        sa.Column("code_verifier", sa.String(length=VERIFIER_LENGTH), nullable=False),
        sa.Column("return_to", sa.String(length=URL_LENGTH), nullable=False),
        _moment("created_at"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_login_attempt_created_at", "login_attempt", ["created_at"])


def upgrade() -> None:
    """Create the four tables and their indexes. Foreign keys only between these tables (D13 is about modules)."""
    _create_app_user()
    _create_user_identity()
    _create_user_session()
    _create_login_attempt()


def downgrade() -> None:
    """Drop the four tables, those that point at app_user first (their indexes go with them)."""
    op.drop_table("login_attempt")
    op.drop_table("user_session")
    op.drop_table("user_identity")
    op.drop_table("app_user")
