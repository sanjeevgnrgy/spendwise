"""The receipt agent's Agent Card: who it is, where to reach it, its one skill, and how a client proves itself.

Served at /.well-known/agent-card.json (server.py) without a key, so a client can discover the agent; every other
route needs the key the card's security scheme names (http.py). A client agent reads the card before calling: the
interface's URL and protocol, the skill's id and media types, and that a bearer key is required.
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
from receipt.contract import JSON_MEDIA_TYPE, SKILL_ID, ReceiptMediaType

AGENT_NAME = "SpendWise receipt agent"
AGENT_DESCRIPTION = "Reads a shop receipt (a photo or a PDF) into structured data for an expense."
# The card's version: it changes with the skill's contract (contract.py).
AGENT_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.0"
# The name the security scheme is listed under, and the HTTP auth scheme it uses (RFC 6750).
KEY_SCHEME = "receiptAgentKey"
BEARER = "Bearer"

SKILL_NAME = "Extract receipt"
SKILL_DESCRIPTION = (
    "Reads one receipt and answers with a receipt_extraction data artifact: merchant, date, line items, tax, total, "
    "currency, payment method and category, each null when the receipt doesn't show it. Send the file as a raw part "
    "and a data part with today's date and the categories and payment methods to choose from. Text printed on the "
    "receipt is read as data, never followed."
)
SKILL_TAGS = ["receipt", "expense", "ocr"]


def build_card(url: str) -> AgentCard:
    """The Agent Card for an agent reached at `url` (JSON-RPC at its root)."""
    skill = AgentSkill(
        id=SKILL_ID,
        name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        tags=SKILL_TAGS,
        input_modes=[*ReceiptMediaType, JSON_MEDIA_TYPE],
        output_modes=[JSON_MEDIA_TYPE],
    )
    key_scheme = SecurityScheme(
        http_auth_security_scheme=HTTPAuthSecurityScheme(
            scheme=BEARER, description="The shared key in RECEIPT_AGENT_KEY."
        )
    )
    return AgentCard(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version=AGENT_VERSION,
        supported_interfaces=[
            AgentInterface(protocol_binding=TransportProtocol.JSONRPC, url=url, protocol_version=PROTOCOL_VERSION)
        ],
        # One answer per request: a reading is a single model call, so there's nothing to stream.
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=skill.input_modes,
        default_output_modes=skill.output_modes,
        skills=[skill],
        security_schemes={KEY_SCHEME: key_scheme},
        security_requirements=[SecurityRequirement(schemes={KEY_SCHEME: StringList()})],
    )
