"""Building an agent's Agent Card: the shape every SpendWise agent's card shares, from the facts that differ.

Part of the agent kit (D202). Every agent is reached over JSON-RPC at its root, answers each request at once (nothing
to stream), offers one skill, and requires a bearer key; only the names, the texts and the skill differ. Each
agent's card.py describes those as a CardSpec and calls build_card; the card is served at
/.well-known/agent-card.json without a key (server.py), and every other route needs the key the card names (http.py).
"""

from dataclasses import dataclass

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

# The A2A protocol version the cards declare, and the HTTP auth scheme their key uses (RFC 6750).
PROTOCOL_VERSION = "1.0"
BEARER = "Bearer"


@dataclass(frozen=True)
class CardSpec:
    """What one agent's card says: its name, description and version (which changes with its skill's contract), the
    name its key's security scheme is listed under, the setting that holds the key (named in the scheme's
    description), and its one skill."""

    name: str
    description: str
    version: str
    key_scheme: str
    key_setting: str
    skill: AgentSkill


def build_card(spec: CardSpec, url: str) -> AgentCard:
    """The Agent Card for the agent `spec` describes, reached at `url` (JSON-RPC at its root): one non-streaming
    interface, the skill, and a required bearer key."""
    key_scheme = SecurityScheme(
        http_auth_security_scheme=HTTPAuthSecurityScheme(
            scheme=BEARER, description=f"The shared key in {spec.key_setting}."
        )
    )
    return AgentCard(
        name=spec.name,
        description=spec.description,
        version=spec.version,
        supported_interfaces=[
            AgentInterface(protocol_binding=TransportProtocol.JSONRPC, url=url, protocol_version=PROTOCOL_VERSION)
        ],
        # One answer per request (or a question back): nothing to stream.
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=spec.skill.input_modes,
        default_output_modes=spec.skill.output_modes,
        skills=[spec.skill],
        security_schemes={spec.key_scheme: key_scheme},
        security_requirements=[SecurityRequirement(schemes={spec.key_scheme: StringList()})],
    )
