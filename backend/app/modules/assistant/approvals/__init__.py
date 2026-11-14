"""Human in the loop: deletes the assistant may only carry out after the user approves them.

In the web panel the model can't delete at all: whatever it asks, the expense is only looked up and
shown with Approve and Cancel (agent/surfaces.py, WebPanel). The real delete happens when the user presses
Approve, and the server decides WHAT gets deleted from its own record of that card (a snapshot of the
expense), never from what the browser sends.

The record lives in the pending_approval table (persistence/tables.py), managed by three commands, each a
vertical slice in commands/ (the message and its handler in one file):
- RequestApproval, when a card is shown: remember it;
- TakeApproval, when Approve or Cancel arrives: read and forget it in one step, so each card decides once;
- RestoreApproval, if the decision then fails midway: put it back exactly as it was.

The rules: a card works only in its own conversation, only once, and only for TTL_MINUTES; at most
MAX_PENDING are kept. models.py holds the shapes and limits the slices share, store.py the table access they
share. Structured like a domain module, inside the assistant: the rest of the assistant (application/) imports
the names below from this package; module.py registers the handlers from each slice and hands the table over.
"""

from app.modules.assistant.approvals.commands.request_approval import RequestApproval
from app.modules.assistant.approvals.commands.restore_approval import RestoreApproval
from app.modules.assistant.approvals.commands.take_approval import TakeApproval
from app.modules.assistant.approvals.models import (
    APPROVAL_ID_LENGTH,
    MAX_PENDING,
    TTL_MINUTES,
    ApprovalId,
    ExpenseSnapshot,
    PendingCard,
)

__all__ = [
    "APPROVAL_ID_LENGTH",
    "MAX_PENDING",
    "TTL_MINUTES",
    "ApprovalId",
    "ExpenseSnapshot",
    "PendingCard",
    "RequestApproval",
    "RestoreApproval",
    "TakeApproval",
]
