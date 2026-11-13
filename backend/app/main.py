"""The web app: FastAPI, built from the composition root (bootstrap.py)."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import bootstrap, migrations
from app.core.config import API_PREFIX, API_VERSION, MCP_PATH, settings
from app.core.db import engine
from app.core.errors import UnexpectedErrorMiddleware, register_error_handlers
from app.core.logging import setup_logging
from app.modules.mcp import module as mcp_module

HEALTHY = {"status": "ok"}


def create_app() -> FastAPI:
    setup_logging()
    services = bootstrap.build()
    # MCP over HTTP only with a token: an open endpoint would let any local program change expenses.
    mcp_http_app = mcp_module.create_http_app(services.mcp_server, services.mcp_token) if services.mcp_token else None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Runs once at startup, before the first request is accepted.
        migrations.require_latest()
        async with AsyncExitStack() as stack:
            if mcp_http_app is not None:
                # A mounted app's own startup code doesn't run, so start the MCP session manager here.
                await stack.enter_async_context(services.mcp_server.session_manager.run())
            yield

    app = FastAPI(title="SpendWise API", version=API_VERSION, lifespan=lifespan)
    # Shared services for routes (core/dependencies.py): one bus and one clock for the whole app.
    app.state.bus = services.bus
    app.state.clock = services.clock
    register_error_handlers(app)
    # Added before CORS, so it sits inside it: even an unexpected error's 500 carries the CORS headers,
    # and the browser can read the problem instead of reporting a network error.
    app.add_middleware(UnexpectedErrorMiddleware)

    # The web app (Vite, port 5173) is a different origin from this API (port 8000), so browsers
    # block it from reading our responses unless we say it's allowed. Only the listed origins are;
    # any other website a user visits still can't use this API through their browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        # So the browser lets the web app read where a new expense lives (201 Created).
        expose_headers=["Location"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        # Cheap enough to call often: checks the server is up and can reach its database.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return HEALTHY

    for router in bootstrap.api_routers(services):
        app.include_router(router, prefix=API_PREFIX)
    if mcp_http_app is not None:
        # MCP clients connect to http://127.0.0.1:8000/mcp/ with "Authorization: Bearer <MCP_TOKEN>".
        app.mount(MCP_PATH, mcp_http_app)
    return app


app = create_app()
