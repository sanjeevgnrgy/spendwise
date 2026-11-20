"""The receipt agent over A2A: A2AReceiptReader, the adapter behind the ReceiptReader port (port.py).

Adapter: the assistant as a client agent. For each reading it fetches the receipt agent's Agent Card from
RECEIPT_AGENT_URL, checks it's the agent we expect (the extract_receipt skill, served at that same address), sends one
SendMessage (the file as a raw part, the choices as a data part, with the key), and reads the finished task: its id,
its state and its receipt_extraction artifact, validated as outside data (D199). The composition root builds it
from the settings through module.py and passes it in; nothing here reads a setting.

The A2A SDK is async, but the receipt turn runs in a plain worker thread (FastAPI runs a sync stream there), so each
reading gets its own short event loop, as the MCP adapter does.
"""

import asyncio
import logging
import re
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_part, new_raw_part
from a2a.types import AgentCard, Message, Role, SendMessageConfiguration, SendMessageRequest, Task, TaskState
from a2a.utils.constants import TransportProtocol
from pydantic import SecretStr, ValidationError

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

# What we expect of the agent (its contract, agents/receipt/contract.py): the skill we call, the artifact it answers.
SKILL_ID = "extract_receipt"
ARTIFACT_NAME = "receipt_extraction"
JSON_MEDIA_TYPE = "application/json"
# One reading is one Gemini call, which the agent's adapter may try twice for up to 60 s each: wait a little longer.
TIMEOUT_SECONDS = 150
# A task id is the agent's, so it's outside data: shown only if it looks like an id (a UUID does).
TASK_ID_PATTERN = r"[A-Za-z0-9_-]{1,64}"
# Why the agent couldn't be used, for the log (never shown to a person: D180).
NO_KEY = "RECEIPT_AGENT_KEY isn't set"
WRONG_CARD = "the card at {url} doesn't offer {skill} over JSON-RPC at that address"
NO_TASK = "the agent answered without a task"


class A2AReceiptReader:
    """ReceiptReader over A2A, to the receipt agent at `url`, with its shared `key`."""

    def __init__(
        self, url: str, key: SecretStr | None, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """`url` is the agent's base address (its card is under it); `key` the shared key, None if it isn't set (then
        every reading is refused). `transport` replaces the network, e.g. httpx.ASGITransport around the agent's app."""
        self._url = url.rstrip("/")
        self._key = key
        self._transport = transport

    def read(self, data: bytes, media_type: str, request: ReadingRequest) -> ReceiptReading:
        """Ask the agent to read one receipt, and wait for the finished task. Raises ReceiptAgentUnavailableError if
        it isn't configured, can't be reached, refuses the key, isn't the agent we expect, or doesn't answer in
        time."""
        if self._key is None:
            logger.warning("receipt agent not used: %s", NO_KEY)
            raise ReceiptAgentUnavailableError(translatable(ChatText.RECEIPT_AGENT_UNAVAILABLE))
        key = self._key.get_secret_value()
        try:
            task = asyncio.run(asyncio.wait_for(self._send(key, data, media_type, request), TIMEOUT_SECONDS))
        except Exception as exc:  # unreachable, 401, a bad card, a timeout, a protocol error...
            # Why is for the log; a person is told only that the receipt reader isn't available (D180).
            logger.warning("receipt agent at %s unavailable: %r", self._url, exc)
            raise ReceiptAgentUnavailableError(translatable(ChatText.RECEIPT_AGENT_UNAVAILABLE)) from exc
        return _reading_of(task, request)

    async def _send(self, key: str, data: bytes, media_type: str, request: ReadingRequest) -> Task:
        """Fetch and check the card, send the message with `key`, and return the finished task."""
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(transport=self._transport, headers=headers, timeout=TIMEOUT_SECONDS) as http:
            card = await A2ACardResolver(httpx_client=http, base_url=self._url).get_agent_card()
            self._check(card)
            client = await create_client(card, ClientConfig(streaming=False, httpx_client=http))
            message = Message(
                role=Role.ROLE_USER,
                message_id=uuid4().hex,
                parts=[new_raw_part(data, media_type), new_data_part(_choices(request), JSON_MEDIA_TYPE)],
            )
            # history_length=0: the answer needn't echo our message, and with it the file, back.
            configuration = SendMessageConfiguration(history_length=0, accepted_output_modes=[JSON_MEDIA_TYPE])
            task = None
            async for response in client.send_message(SendMessageRequest(message=message, configuration=configuration)):
                if response.HasField("task"):
                    task = response.task
        if task is None:
            raise RuntimeError(NO_TASK)
        return task

    def _check(self, card: AgentCard) -> None:
        """Refuse a card that isn't our agent's: it must offer the skill, over JSON-RPC, at the configured address.

        The card is fetched without trust: if it named another address, the key and the receipt would go there.
        """
        offers_skill = any(skill.id == SKILL_ID for skill in card.skills)
        served_here = any(
            interface.protocol_binding == TransportProtocol.JSONRPC and interface.url.rstrip("/") == self._url
            for interface in card.supported_interfaces
        )
        if not (offers_skill and served_here):
            raise ValueError(WRONG_CARD.format(url=self._url, skill=SKILL_ID))


def _choices(request: ReadingRequest) -> dict[str, Any]:
    """The request's data part: the agent's ReadingRequest (today and the values it may choose from)."""
    return {
        "today": request.today.isoformat(),
        "categories": request.categories,
        "payment_methods": request.payment_methods,
    }


def _reading_of(task: Task, request: ReadingRequest) -> ReceiptReading:
    """What the finished task says: its id (if safe to show) and the checked extraction, or None if it wasn't read."""
    task_id = task.id if re.fullmatch(TASK_ID_PATTERN, task.id) else None
    if task.status.state != TaskState.TASK_STATE_COMPLETED:
        # FAILED (the model couldn't read it) or REJECTED (we sent something it doesn't take: a bug on our side).
        logger.warning("receipt task %s ended %s", task_id, TaskState.Name(task.status.state))
        return ReceiptReading(task_id=task_id, extraction=None)
    answers = [part for artifact in task.artifacts if artifact.name == ARTIFACT_NAME for part in artifact.parts]
    found = get_data_parts(answers)
    try:
        if len(found) != 1:
            raise ValueError(f"expected one data part, got {len(found)}")
        extraction = ReceiptExtraction.model_validate(found[0])
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
