"""Human in the loop: actions the assistant may only take after the user approves them.

Today that's deleting an expense: it can't be undone. In the web panel the model isn't offered a way
to delete at all: whatever it asks, a delete runs as a preview, and its card shows Approve and Cancel.
The real delete happens when the user presses Approve, and the server decides WHAT gets deleted from
its own record of that card (a snapshot of the expense), never from what the browser sends.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Final

logger = logging.getLogger("spendwise.approvals")

DELETE_TOOL: Final = "delete_expense"
APPROVE: Final = "approve_delete"
CANCEL: Final = "cancel_delete"
DECISIONS = (APPROVE, CANCEL)

# An unanswered card stops working after this long, and at most this many are remembered.
TTL_SECONDS = 15 * 60
MAX_PENDING = 200


@dataclass
class _Pending:
    expense: dict[str, Any]  # the expense exactly as the card showed it
    created: float


# Cards waiting for a decision: (thread id, card's surface id) -> what it would delete. Kept in memory:
# a restart forgets them, and the user simply asks again. Runs happen in worker threads, hence the lock.
_pending: dict[tuple[str, str], _Pending] = {}
_lock = threading.Lock()


def without_confirmation(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The tool declarations the model sees in the web panel: delete_expense without `confirmed`.

    The model isn't even offered a way to delete by itself, so it has nothing to get wrong.
    """
    changed = []
    for declaration in declarations:
        if declaration["name"] == DELETE_TOOL:
            parameters = declaration["parameters"]
            declaration = {
                **declaration,
                "description": "Ask to delete an expense. Nothing is deleted: the user sees it with Approve and "
                "Cancel buttons, and only their Approve deletes it.",
                "parameters": {
                    **parameters,
                    "properties": {k: v for k, v in parameters["properties"].items() if k != "confirmed"},
                    "required": [r for r in parameters.get("required", []) if r != "confirmed"],
                },
            }
        changed.append(declaration)
    return changed


def guard(arguments: dict[str, Any]) -> dict[str, Any]:
    """A delete call's arguments as they may actually run: always a preview, whatever was sent.

    Only `confirmed=False` is safe to pass on. The MCP tool reads more than just `true` as yes
    (e.g. "true"), so anything else, not only `True`, is replaced.
    """
    if arguments.get("confirmed", False) is not False:
        logger.warning("the model asked to delete without the user's approval; running the preview instead")
    return {**arguments, "confirmed": False}


def _prune() -> None:
    """Forget expired cards, then the oldest ones beyond MAX_PENDING. Call with the lock held."""
    now = time.monotonic()
    for key in [key for key, entry in _pending.items() if now - entry.created > TTL_SECONDS]:
        del _pending[key]
    while len(_pending) > MAX_PENDING:
        del _pending[next(iter(_pending))]  # dicts keep insertion order: the first is the oldest


def request(thread_id: str, surface_id: str, expense: dict[str, Any]) -> None:
    """Remember that this card's Approve may delete this expense, as shown (in this conversation only)."""
    with _lock:
        _pending[(thread_id, surface_id)] = _Pending(expense=expense, created=time.monotonic())
        _prune()


def take(thread_id: str, surface_id: str) -> dict[str, Any] | None:
    """The expense a card was waiting on, forgotten as it's returned: each card decides once."""
    with _lock:
        _prune()
        entry = _pending.pop((thread_id, surface_id), None)
        return entry.expense if entry else None


def restore(thread_id: str, surface_id: str, expense: dict[str, Any]) -> None:
    """Put a card back after a run that failed before anything was deleted, so Approve works again."""
    request(thread_id, surface_id, expense)
