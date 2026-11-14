"""Conversation messages get an index on (thread_id, turn), the shape of every read of a thread.

The conversations module reads a thread by its id and a range of turns: the history from a given turn (the
last 10 turns resent to the model), and the highest turn so far (to number the next one). With only
thread_id indexed, each of those walked every row of the thread; this index finds them directly. Data is
untouched.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app (conversations/persistence/tables.py declares the same index): a
# migration must keep doing exactly what it did, even after the app's code changes.
TABLE = "conversation_message"
INDEX = "ix_conversation_message_thread_id_turn"
# The old one-column index on thread_id: the new index starts with thread_id, so it serves those lookups too.
OLD_INDEX = "ix_conversation_message_thread_id"
OLD_COLUMNS = ["thread_id"]
COLUMNS = ["thread_id", "turn"]


def upgrade() -> None:
    """Add the (thread_id, turn) index and drop the old thread_id one, which it makes redundant.

    No batch mode needed: SQLite can add and drop an index in place, without copying the table.
    """
    op.create_index(INDEX, TABLE, COLUMNS)
    op.drop_index(OLD_INDEX, table_name=TABLE)


def downgrade() -> None:
    """Put the old thread_id index back, then drop the (thread_id, turn) one."""
    op.create_index(OLD_INDEX, TABLE, OLD_COLUMNS)
    op.drop_index(INDEX, table_name=TABLE)
