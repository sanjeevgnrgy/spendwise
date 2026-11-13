"""Expenses get a version number, raised on every change (optimistic concurrency).

A delete can then say "only if it's still the version I showed the user", checked in the same SQL
statement as the delete: the assistant's Approve uses it, so an edit made after the card was shown
can't be deleted unseen. Existing expenses start at version 1.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIRST_VERSION = "1"


def upgrade() -> None:
    # Batch mode: SQLite can't add a NOT NULL column in place, so Alembic copies the table.
    with op.batch_alter_table("expense") as batch:
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default=FIRST_VERSION))


def downgrade() -> None:
    with op.batch_alter_table("expense") as batch:
        batch.drop_column("version")
