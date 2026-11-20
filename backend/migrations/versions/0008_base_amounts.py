"""Every expense is also stored in the base currency, INR: its amount, the rate and the rate's date (Phase 25, D204).

- expense.base_amount_minor (paise), expense.exchange_rate (the rate as exact text) and expense.rate_date, all
  nullable.
- Existing expenses in INR are filled in here: their own amount, rate "1", their own date.
- Existing expenses in another currency stay null: converting them needs the currency agent, which a migration
  must not call. They're left out of totals until they're edited (a new amount, currency or date converts them).

Downgrade drops the three columns (the INR amounts of foreign expenses are lost with them).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here, not imported from the app: a migration must keep doing exactly what it did, even after the app's
# code changes.
BASE_CURRENCY = "INR"
IDENTITY_RATE = "1"
RATE_LENGTH = 32


def upgrade() -> None:
    """Add the three columns, then fill them in for expenses already in INR."""
    # Batch mode, as in 0003: SQLite changes tables by copying them.
    with op.batch_alter_table("expense") as batch:
        batch.add_column(sa.Column("base_amount_minor", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("exchange_rate", sa.String(length=RATE_LENGTH), nullable=True))
        batch.add_column(sa.Column("rate_date", sa.Date(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE expense SET base_amount_minor = amount_minor, exchange_rate = :rate, rate_date = spent_on "
            "WHERE currency = :base"
        ).bindparams(rate=IDENTITY_RATE, base=BASE_CURRENCY)
    )


def downgrade() -> None:
    """Drop the three columns again."""
    with op.batch_alter_table("expense") as batch:
        batch.drop_column("rate_date")
        batch.drop_column("exchange_rate")
        batch.drop_column("base_amount_minor")
