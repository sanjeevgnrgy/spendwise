"""Delegation: the assistant handing requests to SpendWise's other A2A agents, and answering their questions (D206).

Inside the assistant, beside tools/ and receipt_agent/ (application/ imports it; it imports agent/ for the events and
call handlers, never application/ or api/):

- skills.py: the skills the server knows how to hand over (insights, currency) and what it sends each;
- directory.py: AgentDirectory, which reads the agents' cards at startup and makes the delegate_to_agent tool;
- delegator.py: Delegator, one per turn: carries out the model's calls, and resumes a task waiting for the person;
- models.py, persistence/, commands/: the waiting task (pending_delegation), RememberTask and TakeTask.
"""

from app.modules.assistant.delegation.delegator import Delegator
from app.modules.assistant.delegation.directory import AgentDirectory
from app.modules.assistant.delegation.models import DELEGATE_TOOL
from app.modules.assistant.delegation.skills import ASK_CURRENCY, ASK_INSIGHTS, delegable_skills

__all__ = ["ASK_CURRENCY", "ASK_INSIGHTS", "DELEGATE_TOOL", "AgentDirectory", "Delegator", "delegable_skills"]
