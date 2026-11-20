"""The delegation's table, pending_delegation: remote agents' tasks waiting for the person's answer.

The delegation's persistence layer. Private to the assistant module: only the delegation commands
(delegation/commands/) read and write it. module.py hands TABLES to the composition root, which collects every
module's tables for the migrations (migration 0009).
"""

from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.modules.assistant.delegation.models import AGENT_NAME_LENGTH, SKILL_ID_LENGTH, TASK_ID_LENGTH
from app.modules.conversations import THREAD_ID_MAX_LENGTH


class PendingDelegation(SQLModel, table=True):
    """A remote agent's task waiting for the person's answer, one per conversation. Private to the assistant module.

    In the database (not in memory) so the answer works whichever server process gets it, and after a restart.
    """

    __tablename__ = "pending_delegation"

    # Whose conversation it is (core.ids.UserId, no foreign key), and which: together, the key. Only the person's
    # next message in that conversation answers it (D190, D206).
    owner_id: int = Field(primary_key=True)
    thread_id: str = Field(primary_key=True, max_length=THREAD_ID_MAX_LENGTH)
    # Which agent and skill (the app's names), and the task to resume (the agent's ids).
    agent: str = Field(max_length=AGENT_NAME_LENGTH)
    skill: str = Field(max_length=SKILL_ID_LENGTH)
    task_id: str = Field(max_length=TASK_ID_LENGTH)
    context_id: str = Field(max_length=TASK_ID_LENGTH)
    # When the agent asked. Forgotten TTL_MINUTES after it; indexed for that.
    created_at: datetime = Field(index=True, sa_type=DateTime(timezone=True))


# The delegation's tables, for the composition root (module.py exports them with the approvals' table).
TABLES = (PendingDelegation,)
