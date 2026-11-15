"""Accounts module: the people who use SpendWise, how they sign in, and their sessions (Phase 22).

This file is the module's public interface. Other code imports ONLY the contract names below, from
`app.modules.accounts`. The tables, the handlers, the use cases and the router stay private; the composition root
(bootstrap.py) plugs those in through module.py.

Inside: commands/ and queries/ hold one message and its handler each; application/ holds the use cases that call
the identity provider (signing in and out) and the session check; domain/ the rules (keys, return paths, profiles);
values.py, models.py what they share; the tables are in persistence/. The provider itself is the IdentityProvider
port (core/identity.py), so nothing here knows which one it is.

Who uses it: the composition root (CALLBACK_PATH and SIGN_IN_PAGE build the provider's addresses; SESSION_LIFETIME and
LOGIN_ATTEMPT_TTL the cookies' lifetimes), and the export script (the names the web app shares). No other module
depends on it yet; Phase 23's per-user data will use UserId.
"""

from app.modules.accounts.models import CurrentUser, SignedInUser
from app.modules.accounts.values import (
    CALLBACK_PATH,
    LOGIN_ATTEMPT_TTL,
    SESSION_LIFETIME,
    SIGN_IN_PAGE,
    SignInFailure,
    SignInParam,
    UserId,
)

__all__ = [
    "CALLBACK_PATH",
    "LOGIN_ATTEMPT_TTL",
    "SESSION_LIFETIME",
    "SIGN_IN_PAGE",
    "CurrentUser",
    "SignInFailure",
    "SignInParam",
    "SignedInUser",
    "UserId",
]
