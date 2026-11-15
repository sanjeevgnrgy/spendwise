"""The web app: FastAPI, built from the composition root (bootstrap.py) (entry point, HTTP adapter).

create_app() puts together the error handling (RFC 9457 problem details), /health, the sign-in routes, every other
module's routes under API_PREFIX behind the X-CSRF and session checks (D186), and, when MCP_TOKEN is set, the MCP
server at MCP_PATH. uvicorn serves `app` (`.\\run.ps1`), and the export script reads its OpenAPI document.
create_app(services) builds the same app around services made elsewhere, e.g. bootstrap.build() with a fake model,
a fake identity provider or another database.

There's no CORS (D184): the web app reaches the API on its own origin, through the Vite dev server's proxy or a
reverse proxy, so no other website is ever allowed to read these responses in a browser.
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import Engine, text
from starlette.types import ASGIApp

from app import bootstrap
from app.bootstrap import Services
from app.infrastructure import migrations
from app.infrastructure.config import API_PREFIX, API_VERSION, MCP_PATH
from app.infrastructure.logging import setup_logging
from app.modules.mcp import module as mcp_module
from app.web.auth import require_csrf, require_user
from app.web.problems import UnexpectedErrorMiddleware, register_error_handlers

logger = logging.getLogger(__name__)

HEALTHY = {"status": "ok"}
# What every module's routes need, sign-in's aside: a request the app itself sent (X-CSRF), then a live session.
# The cheap header check runs first, so a forged request never reaches the database.
PROTECTED = [Depends(require_csrf), Depends(require_user)]

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_app(services: Services | None = None) -> FastAPI:
    """The whole web app, around `services` (by default, bootstrap.build(): the real adapters and database)."""
    setup_logging()
    built = bootstrap.build() if services is None else services
    # MCP over HTTP only with a token: an open endpoint would let any local program change expenses.
    mcp_http_app = mcp_module.create_http_app(built.mcp_server, built.mcp_token) if built.mcp_token else None

    app = FastAPI(title="SpendWise API", version=API_VERSION, lifespan=_lifespan(built, mcp_http_app))
    # Shared services for routes (web/dependencies.py, web/auth.py): one bus and one clock for the whole app, the
    # session check (the accounts module's) and how the cookies are written.
    app.state.bus = built.bus
    app.state.clock = built.clock
    app.state.authenticate = built.sessions.authenticate
    app.state.cookies = built.cookies
    if built.identity.issuer is None:
        logger.warning("Sign-in isn't configured, so nobody can sign in: every API route answers 401 (see OIDC_*).")
    _add_error_handling(app)
    # Registered before the modules' routes, so the OpenAPI document keeps /health first.
    _add_health_check(app, built.engine)
    for router in bootstrap.auth_routers(built):
        app.include_router(router, prefix=API_PREFIX)
    for router in bootstrap.api_routers(built):
        app.include_router(router, prefix=API_PREFIX, dependencies=PROTECTED)
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


def _add_error_handling(app: FastAPI) -> None:
    """Turn every error, including a bug's, into a problem-details response."""
    register_error_handlers(app)
    # The first middleware added sits closest to the routes: anything added later wraps it and sees an ordinary
    # 500 problem, never the exception.
    app.add_middleware(UnexpectedErrorMiddleware)


def _add_health_check(app: FastAPI, engine: Engine) -> None:
    """Add GET /health, which answers HEALTHY once it has reached the database through `engine`."""

    # A route: FastAPI would copy a docstring into the OpenAPI document, so notes go in comments.
    # Cheap enough to call often: checks the server is up and can reach its database.
    @app.get("/health")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return HEALTHY

