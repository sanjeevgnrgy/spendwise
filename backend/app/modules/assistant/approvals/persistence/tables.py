"""The assistant module's one table, pending_approval: delete cards waiting for Approve or Cancel.

The approvals' persistence layer. Private to this module: only the approval commands (approvals/commands/,
through approvals/store.py) read and write it. module.py hands TABLES to the composition root, which collects
every module's tables for the migrations.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlmodel import Field, SQLModel

from app.modules.assistant.approvals.models import APPROVAL_ID_LENGTH
from app.modules.conversations import THREAD_ID_MAX_LENGTH


class PendingApproval(SQLModel, table=True):
    """A delete card waiting for Approve or Cancel. Private to the assistant module.

    In the database (not in memory) so a decision works whichever server process gets the click,
    and after a restart.
    """

    __tablename__ = "pending_approval"  # pyright: ignore[reportAssignmentType]  (SQLModel declares it as declared_attr)

    # The card's surface id: what the browser sends back with the click.
    approval_id: str = Field(primary_key=True, max_length=APPROVAL_ID_LENGTH)
    # Whose card it is (core.ids.UserId; no foreign key: the users table is the accounts module's). Only they can
    # answer it, and the cap on remembered cards counts each person's alone (D190).
    owner_id: int = Field(index=True)
    # The conversation it belongs to: a card can only be answered in its own thread (of its owner's).
    thread_id: str = Field(index=True, max_length=THREAD_ID_MAX_LENGTH)
    # The expense exactly as the card showed it (ExpenseSnapshot, in approvals/models.py). Approve deletes only
    # that version.
    expense: dict[str, Any] = Field(sa_type=JSON)
    # When the card was shown. Cards expire TTL_MINUTES after it, and beyond MAX_PENDING a person's oldest are
    # forgotten (approvals/store.py); indexed for both. A card put back after a failed decision keeps this time.
    created_at: datetime = Field(index=True, sa_type=DateTime(timezone=True))


# This module's tables, for the composition root (module.py exports it).
TABLES = (PendingApproval,)
