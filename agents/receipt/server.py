"""The receipt agent's composition root: build_app wires the pieces; create_app adds the real model and settings.

The only file of the agent that picks the model provider (the monolith's Gemini adapter, D196). __main__.py serves
create_app(settings); a check (or the owner's future tests) calls build_app with a fake model instead, and needs no
network for the model.
"""

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from starlette.applications import Starlette
from starlette.middleware import Middleware

from app.core.llm import StructuredOutputModel
from app.infrastructure.llm.gemini import GeminiModel
from app.infrastructure.logging import setup_logging
from receipt.card import build_card
from receipt.executor import ReceiptExecutor
from receipt.http import AgentGate
from receipt.reader import ReceiptReader
from receipt.settings import AgentSettings
from receipt.task_store import ForgetfulTaskStore

# JSON-RPC requests (SendMessage, GetTask...) go to the agent's root, the URL its card names.
RPC_PATH = "/"
# The agent's own loggers ("receipt.*"), shown beside the monolith's ("app.*", e.g. the Gemini adapter's).
AGENT_LOGGER = "receipt"


def build_app(settings: AgentSettings, llm: StructuredOutputModel) -> Starlette:
    """The agent's web app: its card, the JSON-RPC route, and the gate in front of them, reading with `llm`."""
    card = build_card(settings.url)
    handler = DefaultRequestHandler(
        agent_executor=ReceiptExecutor(ReceiptReader(llm)), task_store=ForgetfulTaskStore(), agent_card=card
    )
    gate = Middleware(
        AgentGate, key=settings.receipt_agent_key, open_paths=frozenset({AGENT_CARD_WELL_KNOWN_PATH})
    )
    return Starlette(
        routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, RPC_PATH)], middleware=[gate]
    )


def create_app(settings: AgentSettings) -> Starlette:
    """The agent as it runs: logging on, Gemini with the key and model from `settings`."""
    setup_logging(loggers=(AGENT_LOGGER,))
    return build_app(settings, GeminiModel(settings.gemini_api_key, settings.gemini_model))
