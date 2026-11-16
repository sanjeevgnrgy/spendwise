"""The web app: FastAPI, built from the composition root (bootstrap.py) (entry point, HTTP adapter).

create_app() puts together the error handling (RFC 9457 problem details), /health, the sign-in routes, every other
module's routes under API_PREFIX behind the X-CSRF and session checks (D186), and the MCP server at MCP_PATH, behind
personal access tokens (D191). uvicorn serves `app` (`.\\run.ps1`), and the export script reads its OpenAPI document.
create_app(services) builds the same app around services made elsewhere, e.g. bootstrap.build() with a fake model,
a fake identity provider or another database.

There's no CORS (D184): the web app reaches the API on its own origin, through Next.js's rewrite or a reverse proxy,
so no other website is ever allowed to read these responses in a browser.
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import Engine, text

from app import bootstrap
from app.bootstrap import Services
from app.infrastructure import migrations
from app.infrastructure.config import API_PREFIX, API_VERSION, MCP_PATH, settings
from app.infrastructure.logging import setup_logging
from app.modules.mcp import module as mcp_module
from app.web.auth import require_csrf, require_user
from app.web.problems import UnexpectedErrorMiddleware, register_error_handlers
from app.web.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

HEALTHY = {"status": "ok"}
# PUBLIC_URL with this scheme means the app is served over HTTPS, so its responses carry HSTS.
HTTPS_SCHEME = "https://"
# What every module's routes need, sign-in's aside: a request the app itself sent (X-CSRF), then a live session.
# The cheap header check runs first, so a forged request never reaches the database.
PROTECTED = [Depends(require_csrf), Depends(require_user)]

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_app(services: Services | None = None) -> FastAPI:
    """The whole web app, around `services` (by default, bootstrap.build(): the real adapters and database)."""
    setup_logging()
    built = bootstrap.build() if services is None else services
    # MCP over HTTP: every request needs a personal access token, and acts only for its owner (D191).
    mcp_http_app = mcp_module.create_http_app(built.mcp_server, built.access_tokens.resolve)

    app = FastAPI(title="SpendWise API", version=API_VERSION, lifespan=_lifespan(built))
    # Shared services for routes (web/dependencies.py, web/auth.py): one bus and one clock for the whole app, the
    # session check (the accounts module's) and how the cookies are written.
    app.state.bus = built.bus
    app.state.clock = built.clock
    app.state.authenticate = built.sessions.authenticate
    app.state.cookies = built.cookies
    # The per-person rate limit on the model-backed routes (web/rate_limits.py).
    app.state.model_quota = built.model_quota
    if built.identity.issuer is None:
        logger.warning("Sign-in isn't configured, so nobody can sign in: every API route answers 401 (see OIDC_*).")
    _add_error_handling(app)
    # Registered before the modules' routes, so the OpenAPI document keeps /health first.
    _add_health_check(app, built.engine)
    for router in bootstrap.auth_routers(built):
        app.include_router(router, prefix=API_PREFIX)
    for router in bootstrap.api_routers(built):
        app.include_router(router, prefix=API_PREFIX, dependencies=PROTECTED)
    # MCP clients connect to http://127.0.0.1:8000/mcp/ with "Authorization: Bearer <personal access token>".
    app.mount(MCP_PATH, mcp_http_app)
    return app


def _lifespan(services: Services) -> Lifespan:
    """The app's start-up and shutdown: check the migrations, and run the MCP session manager."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Runs once at startup, before the first request is accepted; the code after `yield` at shutdown.

        Raises RuntimeError (the app doesn't start) if the database isn't at the latest migration.
        """
        migrations.require_latest(services.engine)
        # A mounted app's own startup code doesn't run, so start the MCP session manager here.
        async with services.mcp_server.session_manager.run():
            yield

    return lifespan


def _add_error_handling(app: FastAPI) -> None:
    """Turn every error, including a bug's, into a problem-details response, and give every response its security
    headers."""
    register_error_handlers(app)
    # The first middleware added sits closest to the routes: anything added later wraps it and sees an ordinary
    # 500 problem, never the exception.
    app.add_middleware(UnexpectedErrorMiddleware)
    # Outside it, so a 500 gets the headers too. The API's and MCP's answers are a person's data: never cached (D193).
    app.add_middleware(
        SecurityHeadersMiddleware,
        data_prefixes=(API_PREFIX, MCP_PATH),
        https=settings.public_url.startswith(HTTPS_SCHEME),
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

