"""Receipts get their table: receipt_file, one row per uploaded receipt (Phase 21).

The receipts module records each upload here: the key its bytes are stored under (in UPLOADS_DIR, never in the
database), the file's type as read from its bytes, its size, and when it came. A new table, so existing data is
untouched; downgrade drops it (the files in UPLOADS_DIR stay where they are).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app (receipts/values.py has the same sizes): a migration must keep doing
# exactly what it did, even after the app's code changes.
TABLE = "receipt_file"
STORAGE_KEY_LENGTH = 32
MEDIA_TYPE_LENGTH = 15


def upgrade() -> None:
    """Create the receipt_file table. The storage key is unique: one file, one row."""
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_key", sa.String(length=STORAGE_KEY_LENGTH), nullable=False),
        sa.Column("media_type", sa.String(length=MEDIA_TYPE_LENGTH), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Unnamed, as the table class declares it (unique=True), so the database and the model agree.
        sa.UniqueConstraint("storage_key"),
    )


def downgrade() -> None:
    """Drop the receipt_file table (the uploaded files themselves are left in UPLOADS_DIR)."""
    op.drop_table(TABLE)
