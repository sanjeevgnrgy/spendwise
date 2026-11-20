"""The receipt agent's composition root: build_app wires the pieces; create_app adds the real model.

The only file of the agent that picks the model provider (the backend's Gemini adapter, D196). __main__.py serves
create_app(settings); a check (or the owner's future tests) calls build_app with a fake model instead, and needs no
network for the model. The web app itself is the agent kit's (agent_kit/server.py, D202).
"""

from starlette.applications import Starlette

from agent_kit.http import request_limit
from agent_kit.server import build_agent_app, start_logging
from app.core.llm import StructuredOutputModel
from app.infrastructure.llm.gemini import GeminiModel
from receipt.card import build_card
from receipt.contract import MAX_RECEIPT_BYTES
from receipt.executor import ReceiptExecutor
from receipt.reader import ReceiptReader
from receipt.settings import AgentSettings

# The agent's own loggers ("receipt.*"), shown beside the kit's and the backend's (e.g. the Gemini adapter's).
AGENT_LOGGER = "receipt"


def build_app(settings: AgentSettings, llm: StructuredOutputModel) -> Starlette:
    """The agent's web app: its card, the JSON-RPC route and the gate in front of them, reading with `llm`. A
    request may carry one receipt of up to 5 MB, as base64."""
    executor = ReceiptExecutor(ReceiptReader(llm))
    limit = request_limit(MAX_RECEIPT_BYTES)
    return build_agent_app(build_card(settings.url), executor, settings.receipt_agent_key, limit)


def create_app(settings: AgentSettings) -> Starlette:
    """The agent as it runs: logging on, Gemini with the key and model from `settings`."""
    start_logging(AGENT_LOGGER)
    return build_app(settings, GeminiModel(settings.gemini_api_key, settings.gemini_model))
