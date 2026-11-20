"""The A2A agents, hosted inside the backend: hosted_agents builds them and the client that reaches them (D207).

Part of the composition root: only bootstrap.py calls it. The receipt, insights and currency agents (agents/) are
still A2A agents, each with its Agent Card, skill, executor and task store, but on this branch they run in the
backend's process, on its port: each agent's web app is built here, with the backend's own model and clock, and the
A2A client reaches it through httpx's ASGI transport, in memory, with no socket and no port of its own. Each gets a
random key made at startup (its gate still checks it), so no agent key is configured anywhere.

The multi-server version, where each agent is its own service on 9001-9003, is the `multi-server` branch.
"""

import secrets
import sys
from collections.abc import Callable

import httpx
from pydantic import SecretStr
from starlette.applications import Starlette

from app.core.clock import Clock
from app.core.llm import LanguageModel
from app.infrastructure.a2a import A2AAgents, AgentEndpoint
from app.infrastructure.config import PROJECT_DIR

# The agents' code lives beside backend/, in agents/ (each agent, and the kit they share).
AGENTS_DIR = PROJECT_DIR / "agents"
# Their loggers, shown beside the backend's (main.create_app).
AGENT_LOGGERS = ("receipt", "insights", "currency", "agent_kit")
# A key made per process: as long as the agents' rule requires (agent_kit/settings.MIN_KEY_LENGTH).
KEY_BYTES = 32


def hosted_agents(llm: LanguageModel, clock: Clock) -> A2AAgents:
    """The three agents, built in this process, and the A2A client that reaches them in memory, by the names the
    modules ask for ("receipt", "insights", "currency"). `llm` reads receipts and writes tips; `clock` dates rates."""
    # The agents import themselves from agents/ ("receipt", "agent_kit"...): that folder joins the import path here,
    # where they're built, rather than in every entry point (uvicorn, seed.py, mcp_stdio.py, the export script).
    if str(AGENTS_DIR) not in sys.path:
        sys.path.append(str(AGENTS_DIR))
    builders = _builders(llm, clock)
    endpoints, transports = {}, {}
    for name, build in builders.items():
        key = secrets.token_urlsafe(KEY_BYTES)
        url, app = build(key)
        endpoints[name] = AgentEndpoint(url, SecretStr(key))
        transports[name] = httpx.ASGITransport(app=app)
    return A2AAgents(endpoints, transports)


def _builders(llm: LanguageModel, clock: Clock) -> dict[str, Callable[[str], tuple[str, Starlette]]]:
    """For each agent, how to build its app with a key: its card's URL and the app. Imported here, after the agents'
    folder is on the import path."""
    from currency.rates import MockRateProvider
    from currency.server import build_app as currency_app
    from currency.settings import AgentSettings as CurrencySettings
    from insights.server import build_app as insights_app
    from insights.settings import AgentSettings as InsightsSettings
    from receipt.server import build_app as receipt_app
    from receipt.settings import AgentSettings as ReceiptSettings

    def receipt(key: str) -> tuple[str, Starlette]:
        """The receipt agent, reading with the backend's model."""
        settings = ReceiptSettings(_env_file=None, receipt_agent_key=key)
        return settings.url, receipt_app(settings, llm)

    def insights(key: str) -> tuple[str, Starlette]:
        """The insights agent, writing tips with the backend's model."""
        settings = InsightsSettings(_env_file=None, insights_agent_key=key)
        return settings.url, insights_app(settings, llm)

    def currency(key: str) -> tuple[str, Starlette]:
        """The currency agent, with the mock rates and the backend's clock."""
        settings = CurrencySettings(_env_file=None, currency_agent_key=key)
        return settings.url, currency_app(settings, MockRateProvider(), clock)

    return {"receipt": receipt, "insights": insights, "currency": currency}
