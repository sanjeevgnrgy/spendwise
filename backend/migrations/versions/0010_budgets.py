"""Monthly budgets get their table, budget (Phase 27, D210).

One row per person and scope: a category's monthly limit, or (category_id null) the overall one, in paise. A unique
index on (owner_id, category_id) allows one budget per category; because SQL treats NULLs as distinct, a partial
unique index on owner_id where category_id is null allows one overall budget. Downgrade drops the table: every budget
is forgotten.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app: a migration must keep doing exactly what it did.
TABLE = "budget"
OWNER_CATEGORY_INDEX = "uq_budget_owner_id_category_id"
OWNER_OVERALL_INDEX = "uq_budget_owner_id_overall"
OVERALL_ROWS = "category_id IS NULL"


def upgrade() -> None:
    """Create budget and its two unique indexes."""
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("limit_minor", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.create_index(OWNER_CATEGORY_INDEX, ["owner_id", "category_id"], unique=True)
        batch_op.create_index(
            OWNER_OVERALL_INDEX,
            ["owner_id"],
            unique=True,
            sqlite_where=sa.text(OVERALL_ROWS),
            postgresql_where=sa.text(OVERALL_ROWS),
        )


def downgrade() -> None:
    """Drop the indexes and the table."""
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.drop_index(OWNER_OVERALL_INDEX)
        batch_op.drop_index(OWNER_CATEGORY_INDEX)
    op.drop_table(TABLE)
