"""The composition root: the one place that knows every module and every adapter, and wires them together.

main.py (the web app), seed.py, mcp_stdio.py and the migrations (for the tables) all build the app from here,
so there's exactly one list of modules, and nothing registers itself as a side effect of being imported.

build() is also the one seam for replacing the outside world: pass it a clock, a language model, expense
tools, a database engine, a file store, an identity provider or a sealer, and everything built from the result (the
bus, the MCP server, the session check, the routes, main.create_app(services)) uses those instead of the real ones.
"""

from dataclasses import dataclass

from fastapi import APIRouter
from mcp.server.mcpserver import MCPServer
from sqlalchemy import Engine, MetaData
from sqlmodel import SQLModel

from app.core.clock import Clock, SystemClock
from app.core.cqrs import MessageBus
from app.core.files import FileStore
from app.core.identity import IdentityProvider
from app.core.llm import LanguageModel
from app.core.rate_limit import RateLimiter
from app.core.sealing import Sealer
from app.infrastructure import db
from app.infrastructure.config import API_PREFIX, settings
from app.infrastructure.files import LocalFileStore
from app.infrastructure.identity import ClientCredentials, OidcIdentityProvider, UnconfiguredIdentityProvider
from app.infrastructure.llm.gemini import GeminiModel
from app.infrastructure.sealing import FernetSealer
from app.modules import accounts
from app.modules.accounts import module as accounts_module
from app.modules.assistant import module as assistant_module
from app.modules.categories import module as categories_module
from app.modules.conversations import module as conversations_module
from app.modules.expenses import module as expenses_module
from app.modules.mcp import module as mcp_module
from app.modules.receipts import module as receipts_module
from app.web.auth import SessionCookies

# Every module with handlers or tables. (The mcp module has neither: it's an adapter over the bus.)
MODULES = (
    accounts_module, categories_module, expenses_module, conversations_module, receipts_module, assistant_module
)


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
    # Personal access tokens (D191): the account routes make them; MCP over HTTP and the stdio server resolve one to
    # the person it acts for.
    access_tokens: accounts_module.AccessTokens
    # The rate limit on the routes that call the language model (D194), per person.
    model_quota: RateLimiter
    # Sign-in (Phase 22): the identity provider (its issuer is None when sign-in isn't configured), the sealer for
    # the ID tokens sessions keep, the session check main.py puts in front of the protected routes, how the cookies
    # are written, and the addresses the provider is given.
    identity: IdentityProvider
    sealer: Sealer
    sessions: accounts_module.SessionGate
    cookies: SessionCookies
    sign_in: accounts_module.SignInConfig


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
    identity: IdentityProvider | None = None,
    sealer: Sealer | None = None,
) -> Services:
    """Everything the app is made of. Each argument left out gets the real one, configured from the settings.

    - clock: the system clock;
    - llm: Gemini, with GEMINI_API_KEY and GEMINI_MODEL (checked on the first model call, not here);
    - tools: this app's own MCP server, called in-process (acting, on each run, for the person signed in);
    - engine: the database in DATABASE_URL (infrastructure/db.engine);
    - files: a folder on disk, UPLOADS_DIR (created on the first upload). A check that uses a copy of the database
      should pass its own too, so uploads don't land among the real ones;
    - identity: the OpenID Connect provider in OIDC_ISSUER (nothing is fetched from it until someone signs in), or,
      if a sign-in setting is missing, one that refuses every sign-in (D185);
    - sealer: Fernet, with SESSION_ENCRYPTION_KEYS.
    """
    clock = SystemClock() if clock is None else clock
    engine = db.engine if engine is None else engine
    bus = build_bus(clock, engine)
    mcp_server = mcp_module.create_server(bus)
    if llm is None:
        # The one place that picks the LLM provider: Gemini, behind the LanguageModel port.
        llm = GeminiModel(settings.gemini_api_key, settings.gemini_model)
    if tools is None:
        # The assistant's tools: this app's own MCP server, in-process. Each run binds them to the signed-in person.
        tools = assistant_module.McpExpenseTools(mcp_server)
    files = LocalFileStore(settings.uploads_dir) if files is None else files
    identity = _identity_provider(clock) if identity is None else identity
    if sealer is None:
        sealer = FernetSealer([key.get_secret_value() for key in settings.session_encryption_keys])
    return Services(
        clock=clock,
        engine=engine,
        bus=bus,
        llm=llm,
        tools=tools,
        files=files,
        mcp_server=mcp_server,
        access_tokens=accounts_module.create_access_tokens(bus, clock),
        model_quota=RateLimiter(clock, settings.model_requests_per_minute, settings.model_requests_per_day),
        identity=identity,
        sealer=sealer,
        sessions=accounts_module.create_session_gate(bus, identity, clock),
        cookies=_session_cookies(),
        sign_in=_sign_in_config(),
    )


def _session_cookies() -> SessionCookies:
    """How the session and login cookies are written: Secure (COOKIE_SECURE), and as long-lived as the session and
    the sign-in attempt they stand for (the server ends either sooner when it must)."""
    return SessionCookies(
        secure=settings.cookie_secure,
        session_max_age=int(accounts.SESSION_LIFETIME.total_seconds()),
        login_max_age=int(accounts.LOGIN_ATTEMPT_TTL.total_seconds()),
    )


def _sign_in_config() -> accounts_module.SignInConfig:
    """The addresses the provider is given, all on PUBLIC_URL (the origin people open the web app at, D184), and the
    role sign-in requires."""
    return accounts_module.SignInConfig(
        redirect_uri=settings.public_url + API_PREFIX + accounts.CALLBACK_PATH,
        signed_out_url=settings.public_url + accounts.SIGN_IN_PAGE,
        required_role=settings.oidc_required_role,
    )


def _identity_provider(clock: Clock) -> IdentityProvider:
    """The one place that picks the sign-in adapter: standard OpenID Connect, configured from the OIDC_* settings, or,
    while one of them (or SESSION_ENCRYPTION_KEYS) is missing, one that refuses every sign-in (fail closed)."""
    missing = settings.missing_for_sign_in()
    issuer, client_id, secret = settings.oidc_issuer, settings.oidc_client_id, settings.oidc_client_secret
    if missing or issuer is None or client_id is None or secret is None:
        return UnconfiguredIdentityProvider(missing)
    return OidcIdentityProvider(
        issuer,
        ClientCredentials(client_id, secret.get_secret_value()),
        clock,
        scopes=settings.oidc_scopes.split(),
        options=settings.oidc_login_options,
        role_claim=settings.oidc_role_claim,
    )


def auth_routers(services: Services) -> list[APIRouter]:
    """The sign-in routes (the accounts module's). main.py mounts them without the session check: they're how a
    session starts and ends."""
    return [accounts_module.create_router(services.bus, services.identity, services.sealer, services.sign_in)]


def api_routers(services: Services) -> list[APIRouter]:
    """Every other module's REST routes; main.py puts the X-CSRF and session checks in front of all of them. Their
    order is the OpenAPI document's order.

    The receipts and assistant routers are built from `services` (the file store, the tools and the model), and share
    one receipt reader: the receipts routes read a receipt on request, the assistant when one is attached in the
    chat. The account router (the signed-in person's sessions and access tokens) gets the bus, the provider and the
    tokens. The others are fixed routers that read the bus and the clock from `app.state` at request time
    (web/dependencies), which create_app sets from the same services.
    """
    reader = receipts_module.create_reader(services.bus, services.files, services.llm)
    return [
        categories_module.router,
        expenses_module.router,
        conversations_module.router,
        receipts_module.create_router(services.bus, services.files, reader),
        assistant_module.create_router(services.bus, services.tools, services.llm, reader),
        accounts_module.create_account_router(services.bus, services.identity, services.access_tokens),
    ]


def metadata() -> MetaData:
    """Every module's tables, for the migrations (backend/migrations/env.py).

    Raises AssertionError if a module's table isn't registered on SQLModel's shared metadata (then the
    migrations wouldn't see it).
    """
    tables = [table for module in MODULES for table in module.TABLES]
    assert all(table.__table__.metadata is SQLModel.metadata for table in tables)
    return SQLModel.metadata
