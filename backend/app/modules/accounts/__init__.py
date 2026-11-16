"""Accounts module: the people who use SpendWise, how they sign in, their sessions, and their personal access tokens
(Phases 22 and 23).

This file is the module's public interface. Other code imports ONLY the contract names below, from
`app.modules.accounts`. The tables, the handlers, the use cases and the router stay private; the composition root
(bootstrap.py) plugs those in through module.py.

Inside: commands/ and queries/ hold one message and its handler each; application/ holds the use cases that call
the identity provider (signing in and out), the session check and the access tokens; domain/ the rules (keys, return
paths, profiles); values.py, models.py and i18n/ what they share; the tables are in persistence/. api.py has the
sign-in routes, account_api.py the signed-in person's own (sessions, tokens). The provider itself is the
IdentityProvider port (core/identity.py), so nothing here knows which one it is.

Who uses it: the composition root (CALLBACK_PATH and SIGN_IN_PAGE build the provider's addresses; SESSION_LIFETIME and
LOGIN_ATTEMPT_TTL the cookies' lifetimes), the export script (the names the web app shares) and seed.py
(FindUsersByEmail). No other module depends on it: their data points at a person through core's UserId (D190).
"""

from app.modules.accounts.models import CurrentUser, SignedInUser
from app.modules.accounts.queries.find_users_by_email import FindUsersByEmail
from app.modules.accounts.values import (
    CALLBACK_PATH,
    DEFAULT_TOKEN_LIFETIME,
    LOGIN_ATTEMPT_TTL,
    MAX_ACCESS_TOKENS,
    MAX_TOKEN_NAME_LENGTH,
    SESSION_LIFETIME,
    SIGN_IN_PAGE,
    SignInFailure,
    SignInParam,
    TokenLifetime,
    UserId,
)

__all__ = [
    "CALLBACK_PATH",
    "DEFAULT_TOKEN_LIFETIME",
    "LOGIN_ATTEMPT_TTL",
    "MAX_ACCESS_TOKENS",
    "MAX_TOKEN_NAME_LENGTH",
    "SESSION_LIFETIME",
    "SIGN_IN_PAGE",
    "CurrentUser",
    "FindUsersByEmail",
    "SignInFailure",
    "SignInParam",
    "SignedInUser",
    "TokenLifetime",
    "UserId",
]
