"""The insights agent's composition root: build_app wires the pieces; create_app adds the real model.

The only file of the agent that picks the model provider (the backend's Gemini adapter, D196). __main__.py serves
create_app(settings); a check calls build_app with a fake model. The web app itself is the agent kit's
(agent_kit/server.py, D202).
"""

from starlette.applications import Starlette

from agent_kit.http import request_limit
from agent_kit.server import build_agent_app, start_logging
from app.core.llm import StructuredOutputModel
from app.infrastructure.llm.gemini import GeminiModel
from insights.card import build_card
from insights.contract import MAX_REQUEST_DATA_BYTES
from insights.executor import InsightsExecutor
from insights.settings import AgentSettings
from insights.tips import TipWriter

# The agent's own loggers ("insights.*").
AGENT_LOGGER = "insights"


def build_app(settings: AgentSettings, llm: StructuredOutputModel) -> Starlette:
    """The agent's web app: its card, the JSON-RPC route and the gate in front of them, writing tips with `llm`. A
    request may carry a few months of expenses (MAX_REQUEST_DATA_BYTES)."""
    executor = InsightsExecutor(TipWriter(llm))
    limit = request_limit(MAX_REQUEST_DATA_BYTES)
    return build_agent_app(build_card(settings.url), executor, settings.insights_agent_key, limit)


def create_app(settings: AgentSettings) -> Starlette:
    """The agent as it runs: logging on, Gemini with the key and model from `settings`."""
    start_logging(AGENT_LOGGER)
    return build_app(settings, GeminiModel(settings.gemini_api_key, settings.gemini_model))
