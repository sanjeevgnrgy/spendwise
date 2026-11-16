"""Every person's data gets its owner, access tokens get their table, and sessions remember their browser (Phase 23).

- expense, conversation_message, pending_approval, receipt_file: a NOT NULL owner_id (SpendWise's user id, no
  foreign key: the users table belongs to another module). The indexes start with it now, since every read is one
  person's: expense (owner_id, spent_on) replaces spent_on alone; conversation_message (owner_id, thread_id, turn)
  replaces (thread_id, turn).
- access_token: personal access tokens for MCP clients (only each token's SHA-256 is stored).
- user_session.user_agent: the browser a session was signed in from, for the person's list of sessions.

**The rows made before sign-in existed are deleted first** (expenses, conversations, delete cards, receipts), by
the owner's choice: they belong to nobody, so they could never be shown again. Categories are shared and stay.
The receipt files themselves stay in UPLOADS_DIR (a migration doesn't touch files: a check run against a copy of
the database must never delete the real uploads); nothing points at them any more, and they can be removed by hand.

Downgrade removes the new columns, indexes and table and restores the old indexes. It can't bring back the deleted
rows, and it keeps the rows made since (without their owners, so everyone would share them again).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app: a migration must keep doing exactly what it did, even after the app's
# code changes.
OWNED_TABLES = ("expense", "conversation_message", "pending_approval", "receipt_file")
KEY_HASH_LENGTH = 64
TOKEN_NAME_LENGTH = 50
TOKEN_HINT_LENGTH = 4
USER_AGENT_LENGTH = 255


def _moment(name: str, nullable: bool = False) -> sa.Column:
    """A timestamp column, stored with its time zone (the app writes UTC)."""
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _owner() -> sa.Column:
    """The owner column every person's table gets."""
    return sa.Column("owner_id", sa.Integer(), nullable=False)


def _create_access_token() -> None:
    """access_token: one person's token for MCP clients, by its hash."""
    op.create_table(
        "access_token",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("name", sa.String(length=TOKEN_NAME_LENGTH), nullable=False),
        # Unnamed, as the table class declares it, so the database and the model agree.
        sa.Column("token_hash", sa.String(length=KEY_HASH_LENGTH), nullable=False, unique=True),
        sa.Column("hint", sa.String(length=TOKEN_HINT_LENGTH), nullable=False),
        _moment("created_at"),
        _moment("expires_at"),
        _moment("last_used_at", nullable=True),
    )
    op.create_index("ix_access_token_user_id", "access_token", ["user_id"])


def upgrade() -> None:
    """Delete the ownerless rows, then add the owner columns and their indexes, the user agent, and access_token."""
    # Ownerless rows first: a NOT NULL column can't be added to a table that has rows and no value for them.
    for table in OWNED_TABLES:
        op.execute(sa.text(f"DELETE FROM {table}"))
    # batch mode: SQLite can't add a NOT NULL column or change indexes in place, so the table is rebuilt.
    with op.batch_alter_table("expense") as batch:
        batch.add_column(_owner())
        batch.drop_index("ix_expense_spent_on")
        batch.create_index("ix_expense_owner_id_spent_on", ["owner_id", "spent_on"])
    with op.batch_alter_table("conversation_message") as batch:
        batch.add_column(_owner())
        batch.drop_index("ix_conversation_message_thread_id_turn")
        batch.create_index("ix_conversation_message_owner_id_thread_id_turn", ["owner_id", "thread_id", "turn"])
    with op.batch_alter_table("pending_approval") as batch:
        batch.add_column(_owner())
        batch.create_index("ix_pending_approval_owner_id", ["owner_id"])
    with op.batch_alter_table("receipt_file") as batch:
        batch.add_column(_owner())
        batch.create_index("ix_receipt_file_owner_id", ["owner_id"])
    with op.batch_alter_table("user_session") as batch:
        batch.add_column(sa.Column("user_agent", sa.String(length=USER_AGENT_LENGTH), nullable=True))
    _create_access_token()


def downgrade() -> None:
    """Drop access_token and the new columns, and put back the old indexes (deleted rows aren't restored)."""
    op.drop_table("access_token")
    with op.batch_alter_table("user_session") as batch:
        batch.drop_column("user_agent")
    with op.batch_alter_table("receipt_file") as batch:
        batch.drop_index("ix_receipt_file_owner_id")
        batch.drop_column("owner_id")
    with op.batch_alter_table("pending_approval") as batch:
        batch.drop_index("ix_pending_approval_owner_id")
        batch.drop_column("owner_id")
    with op.batch_alter_table("conversation_message") as batch:
        batch.drop_index("ix_conversation_message_owner_id_thread_id_turn")
        batch.create_index("ix_conversation_message_thread_id_turn", ["thread_id", "turn"])
        batch.drop_column("owner_id")
    with op.batch_alter_table("expense") as batch:
        batch.drop_index("ix_expense_owner_id_spent_on")
        batch.create_index("ix_expense_spent_on", ["spent_on"])
        batch.drop_column("owner_id")
