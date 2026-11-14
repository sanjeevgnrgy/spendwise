"""The web app: FastAPI, built from the composition root (bootstrap.py) (entry point, HTTP adapter).

create_app() puts together the error handling (RFC 9457 problem details), CORS, /health, every module's
routes under API_PREFIX and, when MCP_TOKEN is set, the MCP server at MCP_PATH. uvicorn serves `app`
(`.\\run.ps1`), and the export script reads its OpenAPI document. create_app(services) builds the same app
around services made elsewhere, e.g. bootstrap.build() with a fake model or another database.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine, text
from starlette.types import ASGIApp

from app import bootstrap, migrations
from app.bootstrap import Services
from app.core.config import API_PREFIX, API_VERSION, MCP_PATH, settings
from app.core.errors import UnexpectedErrorMiddleware, register_error_handlers
from app.core.logging import setup_logging
from app.modules.mcp import module as mcp_module

HEALTHY = {"status": "ok"}

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_app(services: Services | None = None) -> FastAPI:
    """The whole web app, around `services` (by default, bootstrap.build(): the real adapters and database)."""
    setup_logging()
    built = bootstrap.build() if services is None else services
    # MCP over HTTP only with a token: an open endpoint would let any local program change expenses.
    mcp_http_app = mcp_module.create_http_app(built.mcp_server, built.mcp_token) if built.mcp_token else None

    app = FastAPI(title="SpendWise API", version=API_VERSION, lifespan=_lifespan(built, mcp_http_app))
    # Shared services for routes (core/dependencies.py): one bus and one clock for the whole app.
    app.state.bus = built.bus
    app.state.clock = built.clock
    _add_error_handling_and_cors(app)
    # Registered before the modules' routes, so the OpenAPI document keeps /health first.
    _add_health_check(app, built.engine)
    for router in bootstrap.api_routers(built):
        app.include_router(router, prefix=API_PREFIX)
    if mcp_http_app is not None:
        # MCP clients connect to http://127.0.0.1:8000/mcp/ with "Authorization: Bearer <MCP_TOKEN>".
        app.mount(MCP_PATH, mcp_http_app)
    return app


def _lifespan(services: Services, mcp_http_app: ASGIApp | None) -> Lifespan:
    """The app's start-up and shutdown: check the migrations, and run the MCP session manager if it's mounted."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Runs once at startup, before the first request is accepted; the code after `yield` at shutdown.

        Raises RuntimeError (the app doesn't start) if the database isn't at the latest migration.
        """
        migrations.require_latest(services.engine)
        async with AsyncExitStack() as stack:
            if mcp_http_app is not None:
                # A mounted app's own startup code doesn't run, so start the MCP session manager here.
                await stack.enter_async_context(services.mcp_server.session_manager.run())
            yield

    return lifespan


def _add_error_handling_and_cors(app: FastAPI) -> None:
    """Turn every error into a problem-details response, and let the web app's origins read the responses."""
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


def _add_health_check(app: FastAPI, engine: Engine) -> None:
    """Add GET /health, which answers HEALTHY once it has reached the database through `engine`."""

    # A route: FastAPI would copy a docstring into the OpenAPI document, so notes go in comments.
    # Cheap enough to call often: checks the server is up and can reach its database.
    @app.get("/health")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return HEALTHY

