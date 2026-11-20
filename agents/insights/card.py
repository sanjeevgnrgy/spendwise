"""The insights agent's Agent Card: who it is, where to reach it, its one skill, and how a client proves itself.

Served at /.well-known/agent-card.json without a key (agent_kit/server.py); every other route needs the key the
card's security scheme names (agent_kit/http.py). The skill's description and examples are what a client agent (or a
model choosing among agents, Phase 25 part 3) reads to know what to send, and that the task may ask which month.
"""

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    HTTPAuthSecurityScheme,
    SecurityRequirement,
    SecurityScheme,
    StringList,
)
from a2a.utils.constants import TransportProtocol

from insights.contract import JSON_MEDIA_TYPE, SKILL_ID, TEXT_MEDIA_TYPE

AGENT_NAME = "SpendWise insights agent"
AGENT_DESCRIPTION = "Analyses a month of spending: trends, unusual spends, a month-end forecast and saving tips."
# The card's version: it changes with the skill's contract (contract.py).
AGENT_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.0"
KEY_SCHEME = "insightsAgentKey"
BEARER = "Bearer"

SKILL_NAME = "Analyse spending"
SKILL_DESCRIPTION = (
    "Analyses one month of a person's expenses (in INR) and answers with an insights data artifact: the month's total "
    "and the previous month's, each category's trend, unusual spends, a month-end forecast for the running month, and "
    "3 saving tips. Send one data part {today, month?, question?, expenses: [{spent_on, amount, category, merchant, "
    "payment_method}]}. Without a month, if the expenses span several months, the task stops input-required asking "
    "which month: resume the same task with the answer as text ('November', '2026-11', 'last month')."
)
SKILL_TAGS = ["spending", "insights", "forecast", "budget"]
SKILL_EXAMPLES = ["Where did my money go this month?", "Any unusual spending in October?", "How will this month end?"]


def build_card(url: str) -> AgentCard:
    """The Agent Card for an agent reached at `url` (JSON-RPC at its root)."""
    skill = AgentSkill(
        id=SKILL_ID,
        name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        tags=SKILL_TAGS,
        examples=SKILL_EXAMPLES,
        input_modes=[JSON_MEDIA_TYPE, TEXT_MEDIA_TYPE],
        output_modes=[JSON_MEDIA_TYPE],
    )
    key_scheme = SecurityScheme(
        http_auth_security_scheme=HTTPAuthSecurityScheme(
            scheme=BEARER, description="The shared key in INSIGHTS_AGENT_KEY."
        )
    )
    return AgentCard(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version=AGENT_VERSION,
        supported_interfaces=[
            AgentInterface(protocol_binding=TransportProtocol.JSONRPC, url=url, protocol_version=PROTOCOL_VERSION)
        ],
        # One answer per message (or a question): nothing to stream.
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=skill.input_modes,
        default_output_modes=skill.output_modes,
        skills=[skill],
        security_schemes={KEY_SCHEME: key_scheme},
        security_requirements=[SecurityRequirement(schemes={KEY_SCHEME: StringList()})],
    )
