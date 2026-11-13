"""Composition root: the one place that knows every module and wires them into the app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import create_db_and_tables
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging

# Importing a module's router also imports the module itself, which registers its tables
# with SQLModel before create_db_and_tables() runs at startup.
from app.modules.assistant.router import router as assistant_router
from app.modules.categories.router import router as categories_router
from app.modules.expenses.router import router as expenses_router
from app.modules.mcp.server import server as mcp_server

# The MCP server as a small web app speaking "Streamable HTTP", MCP's transport for remote clients.
# stateless + JSON responses: each MCP request is answered on its own, with no per-client
# session kept in memory, which is all our simple request/response tools need.
mcp_http_app = mcp_server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once at startup, before the first request is accepted.
    create_db_and_tables()
    # A mounted app's own startup code doesn't run, so start the MCP session manager here.
    async with mcp_server.session_manager.run():
        yield


setup_logging()
app = FastAPI(title="SpendWise API", version="0.11.0", lifespan=lifespan)
register_error_handlers(app)

# The web app (Vite, port 5173) is a different origin from this API (port 8000), so browsers
# block it from reading our responses unless we say it's allowed. Only the listed origins are;
# any other website a user visits still can't use this API through their browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    # Does no real work, so a monitor can call it often to check the server is up.
    return {"status": "ok"}


app.include_router(expenses_router)
app.include_router(categories_router)
app.include_router(assistant_router)
# MCP clients connect to http://127.0.0.1:8000/mcp/ (the same server, the same services).
app.mount("/mcp", mcp_http_app)
