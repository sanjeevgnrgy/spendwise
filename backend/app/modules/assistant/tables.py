"""The assistant module's one table, pending_approval: delete cards waiting for Approve or Cancel.

Private to this module: only the approval handlers (approvals.py) read and write it. module.py hands
TABLES to the composition root, which collects every module's tables for the migrations.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlmodel import Field, SQLModel

from app.modules.conversations import THREAD_ID_MAX_LENGTH

# The longest card id stored (approvals.ApprovalId checks the same limit in the commands). The ids the
# assistant makes ("approval_" + 32 hex characters, turns.py) fit with room to spare.
APPROVAL_ID_LENGTH = 64


class PendingApproval(SQLModel, table=True):
    """A delete card waiting for Approve or Cancel. Private to the assistant module.

    In the database (not in memory) so a decision works whichever server process gets the click,
    and after a restart.
    """

    __tablename__ = "pending_approval"

    # The card's surface id: what the browser sends back with the click.
    approval_id: str = Field(primary_key=True, max_length=APPROVAL_ID_LENGTH)
    # The conversation it belongs to: a card can only be answered in its own thread.
    thread_id: str = Field(index=True, max_length=THREAD_ID_MAX_LENGTH)
    # The expense exactly as the card showed it (approvals.ExpenseSnapshot). Approve deletes only that version.
    expense: dict[str, Any] = Field(sa_type=JSON)
    # When the card was shown. Cards expire TTL_MINUTES after it, and beyond MAX_PENDING the oldest are
    # forgotten (approvals.py); indexed for both. A card put back after a failed decision keeps this time.
    created_at: datetime = Field(index=True, sa_type=DateTime(timezone=True))


# This module's tables, for the composition root (module.py exports it).
TABLES = (PendingApproval,)
