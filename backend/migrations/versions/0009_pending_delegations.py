"""Remote agents' tasks waiting for the person's answer get their table, pending_delegation (Phase 25, D206).

One row per conversation (owner_id, thread_id) whose last delegation stopped input-required: the agent, the skill and
the A2A task and context ids to resume it with, and when it asked (rows older than 15 minutes are forgotten by the
app). Downgrade drops the table: any question still waiting is forgotten.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app: a migration must keep doing exactly what it did.
THREAD_ID_LENGTH = 32
AGENT_NAME_LENGTH = 32
SKILL_ID_LENGTH = 64
TASK_ID_LENGTH = 64
TABLE = "pending_delegation"
CREATED_AT_INDEX = "ix_pending_delegation_created_at"


def upgrade() -> None:
    """Create pending_delegation and its index on created_at."""
    op.create_table(
        TABLE,
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=THREAD_ID_LENGTH), nullable=False),
        sa.Column("agent", sa.String(length=AGENT_NAME_LENGTH), nullable=False),
        sa.Column("skill", sa.String(length=SKILL_ID_LENGTH), nullable=False),
        sa.Column("task_id", sa.String(length=TASK_ID_LENGTH), nullable=False),
        sa.Column("context_id", sa.String(length=TASK_ID_LENGTH), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id", "thread_id"),
    )
    op.create_index(CREATED_AT_INDEX, TABLE, ["created_at"])


def downgrade() -> None:
    """Drop the table (and its index)."""
    op.drop_index(CREATED_AT_INDEX, table_name=TABLE)
    op.drop_table(TABLE)
