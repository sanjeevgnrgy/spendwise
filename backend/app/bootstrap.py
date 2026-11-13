"""The composition root: the one place that knows every module and wires them together.

main.py (the web app), seed.py, mcp_stdio.py and the migrations all build the app from here, so
there's exactly one list of modules, and nothing registers itself as a side effect of being imported.
"""

from dataclasses import dataclass

from fastapi import APIRouter
from mcp.server.mcpserver import MCPServer
from sqlalchemy import MetaData
from sqlmodel import SQLModel

from app.core.clock import Clock, SystemClock
from app.core.config import settings
from app.core.cqrs import MessageBus
from app.core.db import new_session
from app.core.llm import LanguageModel
from app.core.llm.gemini import GeminiModel
from app.modules.assistant import module as assistant_module
from app.modules.categories import module as categories_module
from app.modules.conversations import module as conversations_module
from app.modules.expenses import module as expenses_module
from app.modules.mcp import module as mcp_module

# Every module with handlers or tables. (The mcp module has neither: it's an adapter over the bus.)
MODULES = (categories_module, expenses_module, conversations_module, assistant_module)


@dataclass(frozen=True)
class Services:
    clock: Clock
    bus: MessageBus
    llm: LanguageModel
    mcp_server: MCPServer
    # The MCP token, if MCP over HTTP is enabled (see MCP_TOKEN in .env.example).
    mcp_token: str | None


def build_bus(clock: Clock) -> MessageBus:
    bus = MessageBus(new_session, clock)
    for module in MODULES:
        module.register_handlers(bus)
    return bus


def build(clock: Clock | None = None, llm: LanguageModel | None = None) -> Services:
    """Everything the app is made of. Pass a clock or a language model to replace the real ones."""
    clock = clock or SystemClock()
    bus = build_bus(clock)
    token = settings.mcp_token.get_secret_value() if settings.mcp_token else None
    return Services(
        clock=clock,
        bus=bus,
        # The one place that picks the LLM provider: Gemini, behind the LanguageModel port.
        llm=llm or GeminiModel(),
        mcp_server=mcp_module.create_server(bus),
        mcp_token=token,
    )


def api_routers(services: Services) -> list[APIRouter]:
    # The assistant's tools: this app's own MCP server in-process, unless MCP_URL points elsewhere.
    tools = assistant_module.McpExpenseTools(settings.mcp_url or services.mcp_server, token=services.mcp_token)
    return [
        categories_module.router,
        expenses_module.router,
        conversations_module.router,
        assistant_module.create_router(services.bus, tools, services.llm),
    ]


def metadata() -> MetaData:
    """Every module's tables, for the migrations (backend/migrations/env.py)."""
    tables = [table for module in MODULES for table in module.TABLES]
    assert all(table.__table__.metadata is SQLModel.metadata for table in tables)
    return SQLModel.metadata
