"""The receipt agent through the remote-agents port: AgentReceiptReader, the adapter behind ReceiptReader (port.py).

Adapter: the assistant as the receipt agent's client agent. It sends the file and the choices to the agent named
RECEIPT_AGENT for the extract_receipt skill, through core/agents.RemoteAgents (the A2A details, the card check and
the key are infrastructure/a2a's, D201), and reads the finished task: its id, its outcome, and its receipt_extraction
artifact, validated as outside data (D199). The composition root builds it, through module.py, around the
RemoteAgents it chose.
"""

import logging
import re
from typing import Any

from pydantic import ValidationError

from app.core.agents import AgentTask, AgentUnavailableError, DataPart, FilePart, RemoteAgents, TaskOutcome
from app.core.i18n import translatable
from app.core.money import CURRENCY_PATTERN
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.receipt_agent.port import (
    ReadingRequest,
    ReceiptAgentUnavailableError,
    ReceiptExtraction,
    ReceiptReading,
)

logger = logging.getLogger(__name__)

# The agent's name among the app's remote agents (the composition root registers it under this name), the skill we
# call, and the artifact it answers with (its contract: agents/receipt/contract.py).
RECEIPT_AGENT = "receipt"
SKILL_ID = "extract_receipt"
ARTIFACT_NAME = "receipt_extraction"
# A task id is the agent's, so it's outside data: shown only if it looks like an id (a UUID does).
TASK_ID_PATTERN = r"[A-Za-z0-9_-]{1,64}"


class AgentReceiptReader:
    """ReceiptReader through the app's remote agents (`agents`): the receipt agent reads, this checks its answer."""

    def __init__(self, agents: RemoteAgents) -> None:
        """Keep the remote agents; nothing is sent until a receipt is read."""
        self._agents = agents

    def read(self, data: bytes, media_type: str, request: ReadingRequest) -> ReceiptReading:
        """Ask the receipt agent to read one receipt, and wait for the finished task. Raises
        ReceiptAgentUnavailableError if it isn't configured, can't be reached, refuses us or isn't the agent we
        expect."""
        parts = [FilePart(data=data, media_type=media_type), DataPart(data=_choices(request))]
        try:
            task = self._agents.send(RECEIPT_AGENT, SKILL_ID, parts, ARTIFACT_NAME)
        except AgentUnavailableError as exc:
            # Why is in the log already; a person is told only that the receipt reader isn't available (D180).
            raise ReceiptAgentUnavailableError(translatable(ChatText.RECEIPT_AGENT_UNAVAILABLE)) from exc
        return _reading_of(task, request)


def _choices(request: ReadingRequest) -> dict[str, Any]:
    """The request's data part: the agent's ReadingRequest (today and the values it may choose from)."""
    return {
        "today": request.today.isoformat(),
        "categories": request.categories,
        "payment_methods": request.payment_methods,
    }


def _reading_of(task: AgentTask, request: ReadingRequest) -> ReceiptReading:
    """What the finished task says: its id (if safe to show) and the checked extraction, or None if it wasn't read."""
    task_id = task.task_id if re.fullmatch(TASK_ID_PATTERN, task.task_id) else None
    if task.outcome != TaskOutcome.COMPLETED:
        # FAILED (the model couldn't read it) or REJECTED (we sent something it doesn't take: a bug on our side).
        logger.warning("receipt task %s ended %s", task_id, task.outcome)
        return ReceiptReading(task_id=task_id, extraction=None)
    try:
        if len(task.data) != 1:
            raise ValueError(f"expected one data part, got {len(task.data)}")
        extraction = ReceiptExtraction.model_validate(task.data[0])
    except (ValueError, ValidationError) as exc:
        # The agent's answer is outside data: one we can't use is dropped, its details logged at DEBUG only.
        logger.warning("receipt task %s answered something unusable", task_id)
        logger.debug("  why: %s", exc)
        return ReceiptReading(task_id=task_id, extraction=None)
    logger.info("receipt task %s read: %d line items", task_id, len(extraction.line_items))
    return ReceiptReading(task_id=task_id, extraction=_checked(extraction, request))


def _checked(extraction: ReceiptExtraction, request: ReadingRequest) -> ReceiptExtraction:
    """The agent's answer with what can't be right set to null, as if it came from the model itself: a category not
    offered, a currency that isn't a three-letter code, a total that isn't positive."""
    currency = (extraction.currency or "").strip().upper()
    return extraction.model_copy(
        update={
            "category": extraction.category if extraction.category in request.categories else None,
            "currency": currency if re.fullmatch(CURRENCY_PATTERN, currency) else None,
            "total": extraction.total if extraction.total is not None and extraction.total > 0 else None,
        }
    )
