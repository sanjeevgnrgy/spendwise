"""Baseline: the tables as they were before migrations existed (Phases 3-18).

Until now the app created its tables itself at startup (SQLModel create_all). Those databases
already have these tables, so each one is created only if it's missing: the same migration works
for a brand-new database and for an existing one, whose data is left untouched.

Revision ID: 0001
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing()
    if "category" not in existing:
        op.create_table(
            "category",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("icon", sa.String(length=50), nullable=False),
        )
        op.create_index("ix_category_name", "category", ["name"], unique=True)
    if "expense" not in existing:
        op.create_table(
            "expense",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("amount_minor", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=False),
            sa.Column("merchant", sa.String(length=100), nullable=False),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("spent_on", sa.Date(), nullable=False),
            sa.Column("payment_method", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_expense_spent_on", "expense", ["spent_on"])
        op.create_index("ix_expense_category_id", "expense", ["category_id"])
    if "chatmessage" not in existing:
        op.create_table(
            "chatmessage",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("thread_id", sa.String(length=32), nullable=False),
            sa.Column("turn", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(length=30), nullable=False),
            sa.Column("content", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_chatmessage_thread_id", "chatmessage", ["thread_id"])


def downgrade() -> None:
    op.drop_table("chatmessage")
    op.drop_table("expense")
    op.drop_table("category")
