"""What the delegation slices share: a task waiting for the person's answer, its limits, and the tool's name.

The delegation's shared models (like a domain module's models.py and values.py). The command slices (commands/),
the table (persistence/tables.py), the skills (skills.py) and the delegator (delegator.py) use it.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# The tool the model calls to hand a request to another agent (D206).
DELEGATE_TOOL = "delegate_to_agent"
# A waiting task is answered by the person's next message in its conversation within this many minutes (the owner's
# choice), then forgotten; at most this many are kept for a person.
TTL_MINUTES = 15
MAX_PENDING = 50
# Column and field sizes: an agent's name and a skill's id are short; task and context ids are UUIDs, with room.
AGENT_NAME_LENGTH = 32
SKILL_ID_LENGTH = 64
TASK_ID_LENGTH = 64
# A task id or context id as stored: the agent's, so checked to look like an id before it's kept.
IdText = Annotated[str, Field(min_length=1, max_length=TASK_ID_LENGTH, pattern=r"^[A-Za-z0-9_-]+$")]


# A remote agent's task that stopped to ask the person something (INPUT_REQUIRED): which agent and skill, and the ids
# to resume it with.
class PendingTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: str = Field(max_length=AGENT_NAME_LENGTH)
    skill: str = Field(max_length=SKILL_ID_LENGTH)
    task_id: IdText
    context_id: IdText
