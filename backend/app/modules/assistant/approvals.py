"""Human in the loop: actions the assistant may only take after the user approves them.

Today that's deleting an expense: it can't be undone. The model can ask for a delete, but it only
ever runs as a preview. The real delete happens when the user presses Approve on the card, and the
server decides WHAT gets deleted from its own record of that card, never from what the browser sends.
"""

import logging
import threading
from typing import Any

logger = logging.getLogger("spendwise.approvals")

DELETE_TOOL = "delete_expense"
APPROVE = "approve_delete"
CANCEL = "cancel_delete"
DECISIONS = (APPROVE, CANCEL)

# Cards waiting for a decision: (thread id, card's surface id) -> the expense id it would delete.
# Kept in memory: a restart forgets them, and the user simply asks again. Runs happen in worker
# threads, hence the lock.
_pending: dict[tuple[str, str], int] = {}
_lock = threading.Lock()


def guard(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """The arguments the model's tool call may actually run with: a delete only ever as a preview."""
    if tool_name == DELETE_TOOL and arguments.get("confirmed") is True:
        logger.warning("the model asked to delete without the user's approval; running the preview instead")
        return {**arguments, "confirmed": False}
    return arguments


def request(thread_id: str, surface_id: str, expense_id: int) -> None:
    """Remember that this card's Approve button may delete this expense (in this conversation only)."""
    with _lock:
        _pending[(thread_id, surface_id)] = expense_id


def take(thread_id: str, surface_id: str) -> int | None:
    """The expense a card was waiting on, forgotten as it's returned: each card decides once."""
    with _lock:
        return _pending.pop((thread_id, surface_id), None)
