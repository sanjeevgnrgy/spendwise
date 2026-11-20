"""The RemoteAgents port over A2A: A2AAgents, SpendWise as a client agent of its agents (infrastructure, adapter).

The only code in the backend that uses the A2A SDK. For each message it fetches the agent's Agent Card from the
configured address, checks it (the skill asked for, offered over JSON-RPC at that same address: otherwise the key
and the data would go wherever a card said), sends one non-streaming SendMessage with the agent's key and no history
asked back, and turns the finished task into the port's AgentTask (D201). The composition root builds it from the
settings (one AgentEndpoint per agent) and passes it in; a check passes httpx transports that reach the agents' apps
in-process.

The SDK is async, but its callers run in plain worker threads (FastAPI runs sync routes and streams there), so each
message gets its own short event loop, as the MCP adapter does.
"""

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, get_text_parts, new_data_part, new_raw_part, new_text_part
from a2a.types import AgentCard, Message, Part, Role, SendMessageConfiguration, SendMessageRequest, Task, TaskState
from a2a.utils.constants import TransportProtocol
from pydantic import SecretStr

from app.core.agents import (
    AgentTask,
    AgentUnavailableError,
    DataPart,
    FilePart,
    SkillCard,
    TaskOutcome,
    TaskRef,
    TextPart,
)
from app.core.agents import Part as PortPart

logger = logging.getLogger(__name__)

# How long to wait for one task, card included. The receipt agent's one Gemini call may be tried twice for up to
# 60 s each by its adapter: wait a little longer than that.
TIMEOUT_SECONDS = 150
# How long to wait for a card alone (reading what an agent offers, at startup): an agent that's down shouldn't hold
# the backend up.
CARD_TIMEOUT_SECONDS = 5
JSON_MEDIA_TYPE = "application/json"
_OUTCOMES = {
    TaskState.TASK_STATE_COMPLETED: TaskOutcome.COMPLETED,
    TaskState.TASK_STATE_FAILED: TaskOutcome.FAILED,
    TaskState.TASK_STATE_REJECTED: TaskOutcome.REJECTED,
    TaskState.TASK_STATE_INPUT_REQUIRED: TaskOutcome.INPUT_REQUIRED,
}
# Why an agent couldn't be asked, for the log (never shown to a person: D180).
UNKNOWN_AGENT = "no agent named {agent} is configured"
NO_KEY = "{agent}: its key isn't set"
WRONG_CARD = "the card at {url} doesn't offer {skill} over JSON-RPC at that address"
NOT_SERVED_HERE = "the card at {url} doesn't name JSON-RPC at that address"
NO_TASK = "the agent answered without a task"


@dataclass(frozen=True)
class AgentEndpoint:
    """Where one agent listens (its base URL; the card is under it) and the key it requires (None: not set)."""

    url: str
    key: SecretStr | None


class A2AAgents:
    """RemoteAgents over A2A, to the agents in `endpoints` (by name). `transports` replace the network per agent."""

    def __init__(
        self, endpoints: Mapping[str, AgentEndpoint], transports: Mapping[str, httpx.AsyncBaseTransport] | None = None
    ) -> None:
        """Remember where each agent is; nothing is fetched until the first message."""
        self._endpoints = dict(endpoints)
        self._transports = dict(transports or {})

    def skills(self, agent: str) -> list[SkillCard]:
        """The skills `agent`'s card offers, if the card names JSON-RPC at the agent's configured address. Raises
        AgentUnavailableError if it can't be read (unknown agent, unreachable, a timeout, another address)."""
        endpoint = self._endpoint(agent)
        try:
            card = asyncio.run(asyncio.wait_for(self._card(agent, endpoint), CARD_TIMEOUT_SECONDS))
        except Exception as exc:  # unreachable, a timeout, a malformed card...
            logger.warning("agent %s's card at %s unreadable: %r", agent, endpoint.url, exc)
            raise AgentUnavailableError(f"{agent}'s card unreadable") from exc
        if not _served_at(card, endpoint.url.rstrip("/")):
            logger.warning("agent %s: %s", agent, NOT_SERVED_HERE.format(url=endpoint.url))
            raise AgentUnavailableError(f"{agent}'s card names another address")
        return [
            SkillCard(agent=agent, skill_id=s.id, name=s.name, description=s.description, examples=tuple(s.examples))
            for s in card.skills
        ]

    def send(
        self, agent: str, skill: str, parts: Sequence[PortPart], artifact: str, resume: TaskRef | None = None
    ) -> AgentTask:
        """Send `parts` to `agent` for `skill` (resuming `resume`'s task if given) and return the task once it ends or
        stops to ask. Raises AgentUnavailableError if it can't be asked (unknown, no key, unreachable, 401, a wrong
        card, a protocol error, an unknown task or a timeout)."""
        endpoint = self._endpoint(agent)
        if endpoint.key is None:
            logger.warning("agent not asked: %s", NO_KEY.format(agent=agent))
            raise AgentUnavailableError(NO_KEY.format(agent=agent))
        sending = self._send(agent, endpoint, skill, [_to_a2a(part) for part in parts], resume)
        try:
            task = asyncio.run(asyncio.wait_for(sending, TIMEOUT_SECONDS))
        except Exception as exc:  # unreachable, 401, a bad card, a timeout, a protocol error...
            logger.warning("agent %s at %s unavailable: %r", agent, endpoint.url, exc)
            raise AgentUnavailableError(f"{agent} unavailable") from exc
        return _task_of(task, artifact)

    def _endpoint(self, agent: str) -> AgentEndpoint:
        """The agent's endpoint. Raises AgentUnavailableError for an agent that isn't configured."""
        endpoint = self._endpoints.get(agent)
        if endpoint is None:
            logger.warning("agent not asked: %s", UNKNOWN_AGENT.format(agent=agent))
            raise AgentUnavailableError(UNKNOWN_AGENT.format(agent=agent))
        return endpoint

    async def _card(self, agent: str, endpoint: AgentEndpoint) -> AgentCard:
        """The agent's card, fetched without a key (cards are open)."""
        async with httpx.AsyncClient(transport=self._transports.get(agent), timeout=CARD_TIMEOUT_SECONDS) as http:
            return await A2ACardResolver(httpx_client=http, base_url=endpoint.url.rstrip("/")).get_agent_card()

    async def _send(
        self, agent: str, endpoint: AgentEndpoint, skill: str, parts: list[Part], resume: TaskRef | None
    ) -> Task:
        """Fetch and check the card, send one message with the agent's key, and return the task as it ended (or
        stopped)."""
        url = endpoint.url.rstrip("/")
        key = endpoint.key.get_secret_value() if endpoint.key else ""
        headers = {"Authorization": f"Bearer {key}"}
        transport = self._transports.get(agent)
        async with httpx.AsyncClient(transport=transport, headers=headers, timeout=TIMEOUT_SECONDS) as http:
            card = await A2ACardResolver(httpx_client=http, base_url=url).get_agent_card()
            _check(card, url, skill)
            client = await create_client(card, ClientConfig(streaming=False, httpx_client=http))
            message = Message(role=Role.ROLE_USER, message_id=uuid4().hex, parts=parts)
            if resume is not None:
                # Naming the task (and its context) continues it: the agent picks up where it stopped (D206).
                message.task_id, message.context_id = resume.task_id, resume.context_id
            # history_length=0: the answer needn't echo our message (and any file in it) back.
            configuration = SendMessageConfiguration(history_length=0, accepted_output_modes=[JSON_MEDIA_TYPE])
            task = None
            async for response in client.send_message(SendMessageRequest(message=message, configuration=configuration)):
                if response.HasField("task"):
                    task = response.task
        if task is None:
            raise RuntimeError(NO_TASK)
        return task


def _served_at(card: AgentCard, url: str) -> bool:
    """Whether the card names JSON-RPC at `url`: otherwise the key and the data would go wherever it said."""
    return any(
        interface.protocol_binding == TransportProtocol.JSONRPC and interface.url.rstrip("/") == url
        for interface in card.supported_interfaces
    )


def _check(card: AgentCard, url: str, skill: str) -> None:
    """Refuse a card that doesn't offer `skill` over JSON-RPC at `url`: it isn't the agent we were configured for."""
    if not (any(offered.id == skill for offered in card.skills) and _served_at(card, url)):
        raise ValueError(WRONG_CARD.format(url=url, skill=skill))


def _to_a2a(part: PortPart) -> Part:
    """One of the port's parts as an A2A part."""
    match part:
        case FilePart(data=data, media_type=media_type):
            return new_raw_part(data, media_type)
        case DataPart(data=data):
            return new_data_part(data, JSON_MEDIA_TYPE)
        case TextPart(text=text):
            return new_text_part(text)


def _task_of(task: Task, artifact: str) -> AgentTask:
    """The port's view of a finished task: its ids, outcome, the data of the artifacts named `artifact`, and the
    status message's text."""
    outcome = _OUTCOMES.get(task.status.state, TaskOutcome.OTHER)
    parts = [part for found in task.artifacts if found.name == artifact for part in found.parts]
    message = " ".join(get_text_parts(task.status.message.parts)) if task.status.HasField("message") else ""
    logger.info("agent task %s ended %s", task.id, outcome)
    return AgentTask(
        task_id=task.id,
        context_id=task.context_id,
        outcome=outcome,
        data=get_data_parts(parts),
        message=message or None,
    )
