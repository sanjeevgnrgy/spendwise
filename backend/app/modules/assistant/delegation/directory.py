"""The agents the assistant may delegate to: AgentDirectory reads their cards and makes the delegate_to_agent tool.

Part of the delegation. module.create_router builds it and calls load() as the app starts, so the agents' cards are
read once at startup (D206); an agent that couldn't be read then is tried again before a later turn, at most once
every RETRY_SECONDS, so an agent started after the backend is found without a restart, and one that's down doesn't
slow every message. Only skills both offered by a card and known to the server (skills.py) become choices.

The tool's description is built from the cards' own words (name, description, examples): that's how the model learns
what each agent is for. They're outside data, so each is cut to MAX_CARD_TEXT, and the choices themselves are enums
the server checks again (delegator.py).
"""

import logging
import threading
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.core.agents import AgentUnavailableError, RemoteAgents, SkillCard
from app.core.clock import Clock
from app.core.llm import ToolSpec
from app.core.months import YearMonth
from app.modules.assistant.delegation.models import DELEGATE_TOOL
from app.modules.assistant.delegation.skills import DelegatedSkill

logger = logging.getLogger(__name__)

RETRY_SECONDS = 60
MAX_CARD_TEXT = 600
MAX_REQUEST_LENGTH = 500
# The tool, as the model reads it: what to use it for, then each offered skill in the card's words.
TOOL_DESCRIPTION = (
    "Hand a request to another SpendWise agent, for one of the skills below. The server sends the agent the data it "
    "needs (never put expenses or personal details in the request), and returns its answer as data. If the agent "
    "asks a question instead, ask the user it in your reply; their next message goes to the agent.\nSkills:"
)
SKILL_LINE = "- agent '{agent}', skill '{skill}': {name}. {description} Examples: {examples}"
REQUEST_HELP = (
    "What to ask, in English: the user's question as they meant it, or for a conversion one line such as "
    "'4 USD to INR' or '120 EUR to INR on 2026-11-19'."
)
MONTH_HELP = "Only if the user named the month to analyse: it as YYYY-MM. Leave it out otherwise."


class AgentDirectory:
    """The delegable skills the agents' cards offer, read at startup and re-read for agents that were missing."""

    def __init__(self, agents: RemoteAgents, skills: Sequence[DelegatedSkill], clock: Clock) -> None:
        """Know which skills the server can hand over; nothing is read until load()."""
        self._agents = agents
        self._skills = {(skill.agent, skill.skill_id): skill for skill in skills}
        self._clock = clock
        self._cards: dict[str, list[SkillCard]] = {}
        # When each agent's card was last tried (so a missing one is retried at most every RETRY_SECONDS).
        self._tried: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def load(self) -> None:
        """Read the card of every agent not read yet (and not tried in the last RETRY_SECONDS)."""
        now = self._clock.now()
        for agent in sorted({agent for agent, _ in self._skills}):
            with self._lock:
                last = self._tried.get(agent)
                if agent in self._cards or (last is not None and now - last < timedelta(seconds=RETRY_SECONDS)):
                    continue
                self._tried[agent] = now
            try:
                cards = self._agents.skills(agent)
            except AgentUnavailableError:
                logger.info("agent %s not available for delegation yet", agent)
                continue
            with self._lock:
                self._cards[agent] = [card for card in cards if (agent, card.skill_id) in self._skills]
            logger.info("agent %s offers %s", agent, [card.skill_id for card in self._cards[agent]])

    def offered(self) -> list[tuple[DelegatedSkill, SkillCard]]:
        """Each skill the model may be offered now, with its card (agents missing at startup are tried again)."""
        self.load()
        with self._lock:
            cards = [card for agent_cards in self._cards.values() for card in agent_cards]
        return [(self._skills[(card.agent, card.skill_id)], card) for card in cards]

    @staticmethod
    def tool_spec(offered: list[tuple[DelegatedSkill, SkillCard]]) -> ToolSpec:
        """delegate_to_agent, for the offered skills: their cards in the description, their names as the choices."""
        lines = [
            SKILL_LINE.format(
                agent=card.agent,
                skill=card.skill_id,
                name=card.name[:MAX_CARD_TEXT],
                description=card.description[:MAX_CARD_TEXT],
                examples="; ".join(card.examples)[:MAX_CARD_TEXT],
            )
            for _, card in offered
        ]
        parameters = {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": sorted({card.agent for _, card in offered})},
                "skill": {"type": "string", "enum": sorted({card.skill_id for _, card in offered})},
                "request": {"type": "string", "description": REQUEST_HELP, "maxLength": MAX_REQUEST_LENGTH},
                "month": {"type": "string", "description": MONTH_HELP, "pattern": YearMonth.PATTERN},
            },
            "required": ["agent", "skill", "request"],
        }
        return ToolSpec(name=DELEGATE_TOOL, description="\n".join([TOOL_DESCRIPTION, *lines]), parameters=parameters)
