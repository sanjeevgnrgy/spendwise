"""How the composition root plugs this module in: its handlers, the session check, the access tokens, the routes and
its tables.

The accounts module's wiring. bootstrap.py calls register_handlers() when it builds the bus, create_session_gate()
for the check main.py puts in front of every other module's routes, create_access_tokens() (whose `resolve` the MCP
endpoint and the stdio server use), mounts the sign-in router from create_router() and the account router from
create_account_router() (behind the session check), and gives TABLES to the migrations. Nothing else uses this file.
"""

from fastapi import APIRouter

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.identity import IdentityProvider
from app.core.sealing import Sealer
from app.modules.accounts import account_api, api
from app.modules.accounts.application.access_tokens import AccessTokens
from app.modules.accounts.application.config import SignInConfig
from app.modules.accounts.application.sessions import SessionGate
from app.modules.accounts.application.sign_in import SignInFlow
from app.modules.accounts.application.sign_out import SignOutFlow
from app.modules.accounts.commands.create_access_token import CreateAccessToken, create_access_token
from app.modules.accounts.commands.end_session import EndSession, end_session
from app.modules.accounts.commands.renew_session import RenewSession, renew_session
from app.modules.accounts.commands.revoke_access_token import RevokeAccessToken, revoke_access_token
from app.modules.accounts.commands.revoke_sessions import RevokeSessions, revoke_sessions
from app.modules.accounts.commands.sign_in import SignIn, sign_in
from app.modules.accounts.commands.sign_out_other_sessions import SignOutOtherSessions, sign_out_other_sessions
from app.modules.accounts.commands.sign_out_session import SignOutSession, sign_out_session
from app.modules.accounts.commands.start_login import StartLogin, start_login
from app.modules.accounts.commands.take_login_attempt import TakeLoginAttempt, take_login_attempt
from app.modules.accounts.commands.touch_access_token import TouchAccessToken, touch_access_token
from app.modules.accounts.persistence.tables import TABLES
from app.modules.accounts.queries.find_token_owner import FindTokenOwner, find_token_owner
from app.modules.accounts.queries.find_users_by_email import FindUsersByEmail, find_users_by_email
from app.modules.accounts.queries.get_current_user import GetCurrentUser, get_current_user
from app.modules.accounts.queries.get_session import GetSession, get_session
from app.modules.accounts.queries.get_sign_out import GetSignOut, get_sign_out
from app.modules.accounts.queries.list_access_tokens import ListAccessTokens, list_access_tokens
from app.modules.accounts.queries.list_sessions import ListSessions, list_sessions


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries."""
    bus.register(StartLogin, start_login)
    bus.register(TakeLoginAttempt, take_login_attempt)
    bus.register(SignIn, sign_in)
    bus.register(RenewSession, renew_session)
    bus.register(EndSession, end_session)
    bus.register(RevokeSessions, revoke_sessions)
    bus.register(SignOutSession, sign_out_session)
    bus.register(SignOutOtherSessions, sign_out_other_sessions)
    bus.register(CreateAccessToken, create_access_token)
    bus.register(RevokeAccessToken, revoke_access_token)
    bus.register(TouchAccessToken, touch_access_token)
    bus.register(GetSession, get_session)
    bus.register(GetCurrentUser, get_current_user)
    bus.register(GetSignOut, get_sign_out)
    bus.register(ListSessions, list_sessions)
    bus.register(ListAccessTokens, list_access_tokens)
    bus.register(FindTokenOwner, find_token_owner)
    bus.register(FindUsersByEmail, find_users_by_email)


def create_session_gate(bus: MessageBus, identity: IdentityProvider, clock: Clock) -> SessionGate:
    """The one session check: main.py puts its `authenticate` on the app for web/auth.py's require_user."""
    return SessionGate(bus=bus, identity=identity, clock=clock)


def create_access_tokens(bus: MessageBus, clock: Clock) -> AccessTokens:
    """The personal access tokens (D191): the account routes make them, and the MCP endpoint and the stdio server
    resolve one to the person it acts for (`resolve`)."""
    return AccessTokens(bus=bus, clock=clock)


def create_account_router(bus: MessageBus, identity: IdentityProvider, tokens: AccessTokens) -> APIRouter:
    """The signed-in person's account routes (sessions, access tokens): mounted behind the session check."""
    return account_api.create_account_router(bus, identity, tokens)


def create_router(bus: MessageBus, identity: IdentityProvider, sealer: Sealer, config: SignInConfig) -> APIRouter:
    """The sign-in routes, around the sign-in and sign-out use cases (built here, sharing the provider)."""
    sign_in_flow = SignInFlow(bus=bus, identity=identity, sealer=sealer, config=config)
    sign_out_flow = SignOutFlow(bus=bus, identity=identity, sealer=sealer, config=config)
    return api.create_router(sign_in_flow, sign_out_flow)


__all__ = [
    "TABLES",
    "AccessTokens",
    "SessionGate",
    "SignInConfig",
    "create_access_tokens",
    "create_account_router",
    "create_router",
    "create_session_gate",
    "register_handlers",
]
