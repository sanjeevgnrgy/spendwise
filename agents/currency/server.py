"""The currency agent's composition root: build_app wires the pieces; create_app picks the real ones.

The one place that picks the rate provider (MockRateProvider today; a real API later is a change here, D203) and the
clock. __main__.py serves create_app(settings); a check calls build_app with its own provider and a fixed clock. The
web app itself is the agent kit's (agent_kit/server.py, D202).
"""

from starlette.applications import Starlette

from agent_kit.http import request_limit
from agent_kit.server import build_agent_app, start_logging
from app.core.clock import Clock, SystemClock
from currency.card import build_card
from currency.executor import CurrencyExecutor
from currency.rates import MockRateProvider, RateProvider
from currency.settings import AgentSettings

# The agent's own loggers ("currency.*").
AGENT_LOGGER = "currency"


def build_app(settings: AgentSettings, rates: RateProvider, clock: Clock) -> Starlette:
    """The agent's web app: its card, the JSON-RPC route and the gate in front of them, converting with `rates`. A
    request carries no file, so the smallest request limit applies."""
    executor = CurrencyExecutor(rates, clock)
    return build_agent_app(build_card(settings.url), executor, settings.currency_agent_key, request_limit())


def create_app(settings: AgentSettings) -> Starlette:
    """The agent as it runs: logging on, the mock rates, the system clock."""
    start_logging(AGENT_LOGGER)
    return build_app(settings, MockRateProvider(), SystemClock())
