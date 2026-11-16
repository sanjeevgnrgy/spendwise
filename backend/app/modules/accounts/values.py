"""The accounts module's shared values: ids, column sizes, lifetimes, and the names the web app shares (accounts).

Part of the module's contract layer. The tables (persistence/), the slices (commands/, queries/), the use cases
(application/) and the routes use them; __init__.py exports what the composition root and the web contract need.
This file imports no other file of the module.
"""

import math
from datetime import timedelta
from enum import IntEnum, StrEnum

from app.core.ids import RecordId
from app.core.ids import UserId as UserId  # core's (every module's data points at it); re-exported for accounts

SessionId = RecordId
TokenId = RecordId

# How long a session lives. It's renewed while used (sliding): unused for SESSION_IDLE, it ends; and it ends after
# SESSION_LIFETIME however much it's used, so a stolen cookie can't be kept alive for ever. Renewal is written at
# most once per RENEW_AFTER, not on every request.
SESSION_IDLE = timedelta(days=1)
SESSION_LIFETIME = timedelta(days=14)
RENEW_AFTER = SESSION_IDLE / 2
# How long a sign-in may take at the provider before the attempt is forgotten, and how many unfinished attempts are
# kept at most (the login route needs no session, so anyone could start attempts: older ones are dropped first).
LOGIN_ATTEMPT_TTL = timedelta(minutes=10)
MAX_LOGIN_ATTEMPTS = 500

# Column sizes. A key's hash is SHA-256 in hex; a handle is 128 random bits in hex. An issuer is a URL; a subject is
# up to 255 characters (OpenID Connect Core 1.0, 2); an email up to 320 (RFC 5321's 64 + 1 + 255).
KEY_HASH_LENGTH = 64
HANDLE_LENGTH = 32
MAX_ISSUER_LENGTH = 255
MAX_SUBJECT_LENGTH = 255
MAX_EMAIL_LENGTH = 320
MAX_NAME_LENGTH = 200
MAX_URL_LENGTH = 2048
# state and nonce are random keys (43 characters); a PKCE verifier is 43 to 128 characters (RFC 7636, 4.1).
MAX_STATE_LENGTH = 64
MAX_VERIFIER_LENGTH = 128
MAX_OPTION_LENGTH = 32
# A browser's User-Agent header, kept with its session so the person can tell their sessions apart (Settings).
MAX_USER_AGENT_LENGTH = 255

# Personal access tokens (D191): what MCP clients send as "Authorization: Bearer <token>" to act for their owner.
# A token is the prefix and 32 random bytes in unpadded base64url (43 characters); the prefix makes a leaked one
# recognisable (to a person, or a secret scanner). Only its SHA-256 is stored, plus its last characters as a hint.
ACCESS_TOKEN_PREFIX = "spw_"
ACCESS_TOKEN_BYTES = 32
ACCESS_TOKEN_LENGTH = len(ACCESS_TOKEN_PREFIX) + math.ceil(ACCESS_TOKEN_BYTES * 4 / 3)
TOKEN_HINT_LENGTH = 4
# At most this many tokens per person, each named so it can be told apart (and revoked) later.
MAX_ACCESS_TOKENS = 10
MAX_TOKEN_NAME_LENGTH = 50
# A token's last use is written at most this often, not on every MCP request.
TOKEN_TOUCH_AFTER = timedelta(hours=1)


# How long a new token works, in days: it always expires, so a forgotten one stops working by itself.
class TokenLifetime(IntEnum):
    MONTH = 30
    QUARTER = 90
    YEAR = 365


DEFAULT_TOKEN_LIFETIME = TokenLifetime.QUARTER

# Where the sign-in routes live, under the API prefix. The provider sends people back to CALLBACK_PATH: with
# PUBLIC_URL and the prefix in front, that's the redirect URI registered at the provider.
AUTH_PATH = "/auth"
CALLBACK_PATH = f"{AUTH_PATH}/callback"
# The web app's sign-in page. The callback sends people there when sign-in fails (with ?error=), and signing out
# ends there. Shared with the web app through the generated contract, so its router uses the same path.
SIGN_IN_PAGE = "/sign-in"


# Why a sign-in didn't complete: the callback sends people to SIGN_IN_PAGE?error=<value>, and the web app shows the
# matching text. Only these codes travel: never the provider's own words (D180).
class SignInFailure(StrEnum):
    # The person cancelled at the provider, or it refused them (OAuth's access_denied).
    CANCELLED = "cancelled"
    # The attempt was too old, already used, or started in another browser: start again.
    EXPIRED = "expired"
    # Something in the provider's answer failed a check: nothing from it is trusted.
    REJECTED = "rejected"
    # The person signed in, but may not use SpendWise (no required role, or the account is switched off).
    NOT_ALLOWED = "not-allowed"
    # The provider couldn't be used: not configured, unreachable, or answering with an error.
    UNAVAILABLE = "unavailable"


# The query parameters the sign-in routes read, and SIGN_IN_PAGE's. Shared with the web app (contract).
class SignInParam(StrEnum):
    # GET /auth/login: which button was pressed, and the page to come back to.
    OPTION = "option"
    RETURN_TO = "return_to"
    # GET /auth/logout: the session's public handle, proof the request comes from the app (D186).
    SESSION = "sid"
    # SIGN_IN_PAGE: why the last sign-in failed (SignInFailure).
    ERROR = "error"
