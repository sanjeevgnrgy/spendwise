"""The insights agent's Agent Card: who it is, where to reach it, its one skill, and how a client proves itself.

Served at /.well-known/agent-card.json without a key (agent_kit/server.py); every other route needs the key the
card's security scheme names (agent_kit/http.py). The skill's description and examples are what a client agent (or a
model choosing among agents, Phase 25 part 3) reads to know what to send, and that the task may ask which month.
"""

from a2a.types import AgentCard, AgentSkill

from agent_kit.card import CardSpec
from agent_kit.card import build_card as build_card_from_spec
from insights.contract import JSON_MEDIA_TYPE, SKILL_ID, TEXT_MEDIA_TYPE

AGENT_NAME = "SpendWise insights agent"
AGENT_DESCRIPTION = "Analyses a month of spending: trends, unusual spends, a month-end forecast and saving tips."
# The card's version: it changes with the skill's contract (contract.py).
AGENT_VERSION = "1.0.0"
KEY_SCHEME = "insightsAgentKey"
KEY_SETTING = "INSIGHTS_AGENT_KEY"

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


# What this agent's card says (agent_kit/card.py builds the rest).
SPEC = CardSpec(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    key_scheme=KEY_SCHEME,
    key_setting=KEY_SETTING,
    skill=AgentSkill(
        id=SKILL_ID,
        name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        tags=SKILL_TAGS,
        examples=SKILL_EXAMPLES,
        input_modes=[JSON_MEDIA_TYPE, TEXT_MEDIA_TYPE],
        output_modes=[JSON_MEDIA_TYPE],
    ),
)


def build_card(url: str) -> AgentCard:
    """The Agent Card for this agent reached at `url` (JSON-RPC at its root)."""
    return build_card_from_spec(SPEC, url)
