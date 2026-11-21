"""Building and serving any agent's web app: build_agent_app and serve (agent kit).

Each agent's composition root (receipt/server.py, currency/server.py) passes its card, its executor, its key and its
request limit; this wires the SDK's request handler (with the kit's task store), the Agent Card and JSON-RPC routes,
and the gate in front of them, the same way for every agent (D202). serve() runs it on the kit's host.
"""

import logging

import uvicorn
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.types import AgentCard
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.middleware import Middleware

from agent_kit.http import AgentGate
from agent_kit.settings import HOST
from agent_kit.task_store import ForgetfulTaskStore
from app.infrastructure.logging import setup_logging

# JSON-RPC requests (SendMessage, GetTask...) go to an agent's root, the URL its card names.
RPC_PATH = "/"
# The kit's own loggers ("agent_kit.*"), shown beside the agent's and the backend's.
KIT_LOGGER = "agent_kit"


def build_agent_app(card: AgentCard, executor: AgentExecutor, key: SecretStr, max_request_bytes: int) -> Starlette:
    """An agent's web app: its card (open), the JSON-RPC route (behind the key and the size limit), and the kit's
    forgetful task store."""
    handler = DefaultRequestHandler(agent_executor=executor, task_store=ForgetfulTaskStore(), agent_card=card)
    gate = Middleware(
        AgentGate,
        key=key,
        open_paths=frozenset({AGENT_CARD_WELL_KNOWN_PATH}),
        max_request_bytes=max_request_bytes,
    )
    return Starlette(
        routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, RPC_PATH)], middleware=[gate]
    )


def start_logging(agent_logger: str, level: int = logging.INFO) -> None:
    """Show the agent's own loggers, the kit's and the backend's (the Gemini adapter's) on the console."""
    setup_logging(level, loggers=(agent_logger, KIT_LOGGER))


def serve(app: Starlette, port: int) -> None:
    """Serve `app` on the kit's host (this machine only) at `port`, until stopped (Ctrl+C)."""
    uvicorn.run(app, host=HOST, port=port)
