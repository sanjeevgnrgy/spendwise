"""The currency agent's Agent Card: who it is, where to reach it, its one skill, and how a client proves itself.

Served at /.well-known/agent-card.json without a key (agent_kit/server.py), so a client can discover the agent; every
other route needs the key the card's security scheme names (agent_kit/http.py). The skill's description and examples
are what a client agent (or a model choosing among agents, Phase 25 part 3) reads to know what to send.
"""

from a2a.types import AgentCard, AgentSkill

from agent_kit.card import CardSpec
from agent_kit.card import build_card as build_card_from_spec
from currency.contract import JSON_MEDIA_TYPE, SKILL_ID, TEXT_MEDIA_TYPE

AGENT_NAME = "SpendWise currency agent"
AGENT_DESCRIPTION = "Converts amounts between currencies at the day's exchange rate."
# The card's version: it changes with the skill's contract (contract.py).
AGENT_VERSION = "1.0.0"
# The name the key's security scheme is listed under, and the setting that holds the key.
KEY_SCHEME = "currencyAgentKey"
KEY_SETTING = "CURRENCY_AGENT_KEY"

SKILL_NAME = "Convert currency"
SKILL_DESCRIPTION = (
    "Converts an amount from one currency to another (ISO 4217 codes) at the rate for a given day, and answers with "
    "a conversion data artifact: the amount, both currencies, the rate as a decimal string, the rate's date, the "
    "converted amount and the rate's source. Send one data part {amount, from_currency, to_currency, on?} or one line "
    "of text."
)
SKILL_TAGS = ["currency", "exchange-rate", "conversion"]
SKILL_EXAMPLES = ["4 USD to INR", "120.50 EUR in INR on 2026-11-19"]


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
