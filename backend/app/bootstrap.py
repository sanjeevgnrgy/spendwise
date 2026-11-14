"""The composition root: the one place that knows every module and every adapter, and wires them together.

main.py (the web app), seed.py, mcp_stdio.py and the migrations (for the tables) all build the app from here,
so there's exactly one list of modules, and nothing registers itself as a side effect of being imported.

build() is also the one seam for replacing the outside world: pass it a clock, a language model, expense
tools, a database engine or a file store, and everything built from the result (the bus, the MCP server, the routes,
main.create_app(services)) uses those instead of the real ones.
"""

from dataclasses import dataclass

from fastapi import APIRouter
from mcp.server.mcpserver import MCPServer
from sqlalchemy import Engine, MetaData
from sqlmodel import SQLModel

from app.core.clock import Clock, SystemClock
from app.core.cqrs import MessageBus
from app.core.files import FileStore
from app.core.llm import LanguageModel
from app.infrastructure import db
from app.infrastructure.config import settings
from app.infrastructure.files import LocalFileStore
from app.infrastructure.llm.gemini import GeminiModel
from app.modules.assistant import module as assistant_module
from app.modules.categories import module as categories_module
from app.modules.conversations import module as conversations_module
from app.modules.expenses import module as expenses_module
from app.modules.mcp import module as mcp_module
from app.modules.receipts import module as receipts_module

# Every module with handlers or tables. (The mcp module has neither: it's an adapter over the bus.)
MODULES = (categories_module, expenses_module, conversations_module, receipts_module, assistant_module)


@dataclass(frozen=True)
class Services:
    """Everything the app is made of, built once by build() and shared by every entry point."""

    clock: Clock
    # The database: the bus's sessions, /health and the start-up migration check all use this engine.
    engine: Engine
    bus: MessageBus
    llm: LanguageModel
    # The assistant's expense tools (the assistant's ExpenseTools port).
    tools: assistant_module.ExpenseTools
    # Where uploaded files' bytes are kept (the receipts module's receipts).
    files: FileStore
    mcp_server: MCPServer
    # The MCP token, if MCP over HTTP is enabled (see MCP_TOKEN in .env.example).
    mcp_token: str | None


def build_bus(clock: Clock, engine: Engine) -> MessageBus:
    """The one MessageBus, opening its sessions on `engine`, with every module's handlers registered.

    Raises ValueError if two modules register the same message (a wiring mistake).
    """
    bus = MessageBus(db.session_factory(engine), clock)
    for module in MODULES:
        module.register_handlers(bus)
    return bus


def build(
    clock: Clock | None = None,
    llm: LanguageModel | None = None,
    tools: assistant_module.ExpenseTools | None = None,
    engine: Engine | None = None,
    files: FileStore | None = None,
) -> Services:
    """Everything the app is made of. Each argument left out gets the real one, configured from the settings.

    - clock: the system clock;
    - llm: Gemini, with GEMINI_API_KEY and GEMINI_MODEL (checked on the first model call, not here);
    - tools: this app's own MCP server, called in-process, or the one at MCP_URL if that's set (so a check that
      injects only an engine still reaches a remote server's database when MCP_URL is in .env: pass tools too);
    - engine: the database in DATABASE_URL (infrastructure/db.engine);
    - files: a folder on disk, UPLOADS_DIR (created on the first upload). A check that uses a copy of the database
      should pass its own too, so uploads don't land among the real ones.
    """
    clock = SystemClock() if clock is None else clock
    engine = db.engine if engine is None else engine
    bus = build_bus(clock, engine)
    mcp_server = mcp_module.create_server(bus)
    token = settings.mcp_token.get_secret_value() if settings.mcp_token else None
    if llm is None:
        # The one place that picks the LLM provider: Gemini, behind the LanguageModel port.
        llm = GeminiModel(settings.gemini_api_key, settings.gemini_model)
    if tools is None:
        # The assistant's tools: this app's own MCP server in-process, unless MCP_URL points elsewhere.
        tools = assistant_module.McpExpenseTools(settings.mcp_url or mcp_server, token=token)
    files = LocalFileStore(settings.uploads_dir) if files is None else files
    return Services(
        clock=clock, engine=engine, bus=bus, llm=llm, tools=tools, files=files, mcp_server=mcp_server, mcp_token=token
    )


def api_routers(services: Services) -> list[APIRouter]:
    """Every module's REST routes. Their order is the OpenAPI document's order.

    The receipts and assistant routers are built from `services` (the file store, the tools and the model), and share
    one receipt reader: the receipts routes read a receipt on request, the assistant when one is attached in the
    chat. The others are fixed routers that read the bus and the clock from `app.state` at request time
    (web/dependencies), which create_app sets from the same services.
    """
    reader = receipts_module.create_reader(services.bus, services.files, services.llm)
    return [
        categories_module.router,
        expenses_module.router,
        conversations_module.router,
        receipts_module.create_router(services.bus, services.files, reader),
        assistant_module.create_router(services.bus, services.tools, services.llm, reader),
    ]


def metadata() -> MetaData:
    """Every module's tables, for the migrations (backend/migrations/env.py).

    Raises AssertionError if a module's table isn't registered on SQLModel's shared metadata (then the
    migrations wouldn't see it).
    """
    tables = [table for module in MODULES for table in module.TABLES]
    assert all(table.__table__.metadata is SQLModel.metadata for table in tables)
    return SQLModel.metadata
