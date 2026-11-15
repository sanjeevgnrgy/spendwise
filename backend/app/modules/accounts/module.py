"""How the composition root plugs this module in: its handlers, the session check, the routes and its tables.

The accounts module's wiring. bootstrap.py calls register_handlers() when it builds the bus, create_session_gate()
for the check main.py puts in front of every other module's routes, mounts the router from create_router(), and
gives TABLES to the migrations. Nothing else uses this file.
"""

from fastapi import APIRouter

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.identity import IdentityProvider
from app.core.sealing import Sealer
from app.modules.accounts import api
from app.modules.accounts.application.config import SignInConfig
from app.modules.accounts.application.sessions import SessionGate
from app.modules.accounts.application.sign_in import SignInFlow
from app.modules.accounts.application.sign_out import SignOutFlow
from app.modules.accounts.commands.end_session import EndSession, end_session
from app.modules.accounts.commands.renew_session import RenewSession, renew_session
from app.modules.accounts.commands.revoke_sessions import RevokeSessions, revoke_sessions
from app.modules.accounts.commands.sign_in import SignIn, sign_in
from app.modules.accounts.commands.start_login import StartLogin, start_login
from app.modules.accounts.commands.take_login_attempt import TakeLoginAttempt, take_login_attempt
from app.modules.accounts.persistence.tables import TABLES
from app.modules.accounts.queries.get_current_user import GetCurrentUser, get_current_user
from app.modules.accounts.queries.get_session import GetSession, get_session
from app.modules.accounts.queries.get_sign_out import GetSignOut, get_sign_out


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries."""
    bus.register(StartLogin, start_login)
    bus.register(TakeLoginAttempt, take_login_attempt)
    bus.register(SignIn, sign_in)
    bus.register(RenewSession, renew_session)
    bus.register(EndSession, end_session)
    bus.register(RevokeSessions, revoke_sessions)
    bus.register(GetSession, get_session)
    bus.register(GetCurrentUser, get_current_user)
    bus.register(GetSignOut, get_sign_out)


def create_session_gate(bus: MessageBus, identity: IdentityProvider, clock: Clock) -> SessionGate:
    """The one session check: main.py puts its `authenticate` on the app for web/auth.py's require_user."""
    return SessionGate(bus=bus, identity=identity, clock=clock)


def create_router(bus: MessageBus, identity: IdentityProvider, sealer: Sealer, config: SignInConfig) -> APIRouter:
    """The sign-in routes, around the sign-in and sign-out use cases (built here, sharing the provider)."""
    sign_in_flow = SignInFlow(bus=bus, identity=identity, sealer=sealer, config=config)
    sign_out_flow = SignOutFlow(bus=bus, identity=identity, sealer=sealer, config=config)
    return api.create_router(sign_in_flow, sign_out_flow)


__all__ = ["TABLES", "SessionGate", "SignInConfig", "create_router", "create_session_gate", "register_handlers"]
