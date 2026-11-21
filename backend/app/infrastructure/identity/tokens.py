"""Checking the provider's signed tokens: the ID token after sign-in, and the logout token of a back-channel logout.

Part of the OIDC adapter (infrastructure); oidc.py calls these with the provider's keys (documents.py). PyJWT checks
the signature, the issuer, the audience and that the required claims are present. The times (exp, iat, nbf) are
checked here against the app's injected clock, because PyJWT reads the system clock itself (D185). Every failure is
an InvalidTokenError: the token isn't trusted, whatever else it says.
"""

import hmac
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import PyJWKError, PyJWTError
from jwt.types import Options

from app.core.identity import InvalidTokenError

# Asymmetric signatures only: a token signed with "none", or with an HMAC (HS256, keyed by the client secret), is
# refused, so only the provider's private key can make one we accept.
ALLOWED_ALGORITHMS = frozenset(
    {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512", "EdDSA"}
)
# How far apart our clock and the provider's may be before a token's times count against it.
CLOCK_SKEW = timedelta(seconds=60)
# The claims each token must carry (OpenID Connect Core 1.0, 2; Back-Channel Logout 1.0, 2.4).
ID_TOKEN_CLAIMS = ("iss", "sub", "aud", "exp", "iat")
LOGOUT_TOKEN_CLAIMS = ("iss", "aud", "iat", "jti", "events")
# The event a logout token announces (Back-Channel Logout 1.0, 2.4).
BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"

Claims = dict[str, Any]
# Finds the provider's signing key (a JSON Web Key) by the key id a token's header names (documents.py).
KeyLookup = Callable[[str | None], dict[str, Any]]


def decode_signed(token: str, signing_key: KeyLookup, issuer: str, audience: str, required: Iterable[str]) -> Claims:
    """The token's claims, once its signature, issuer and audience check out and `required` claims are present.

    The algorithm is the header's, if it's an allowed one and the key doesn't name another. Raises InvalidTokenError.
    """
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as error:
        raise InvalidTokenError(f"not a signed token: {error}") from None
    algorithm = header.get("alg")
    if algorithm not in ALLOWED_ALGORITHMS:
        raise InvalidTokenError(f"signature algorithm {algorithm!r} isn't accepted")
    key = signing_key(header.get("kid"))
    if key.get("alg", algorithm) != algorithm:
        raise InvalidTokenError(f"the key is for {key.get('alg')!r}, the token says {algorithm!r}")
    try:
        public_key = jwt.PyJWK(key, algorithm=algorithm).key
        # Times are checked by check_times, against the app's clock; everything else by PyJWT.
        options: Options = {"verify_exp": False, "verify_iat": False, "verify_nbf": False, "require": list(required)}
        return jwt.decode(token, public_key, algorithms=[algorithm], audience=audience, issuer=issuer, options=options)
    except (PyJWTError, PyJWKError) as error:
        raise InvalidTokenError(f"the token failed a check: {error}") from None


def check_times(claims: Claims, now: datetime) -> None:
    """Refuse a token that has expired, or was issued (or becomes valid) in the future, give or take CLOCK_SKEW.

    Raises InvalidTokenError, also for a time that isn't a number.
    """
    moment, skew = now.timestamp(), CLOCK_SKEW.total_seconds()
    for name in ("exp", "iat", "nbf"):
        value = claims.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int | float)):
            raise InvalidTokenError(f"'{name}' isn't a number")
    if claims.get("exp") is not None and moment >= claims["exp"] + skew:
        raise InvalidTokenError("the token has expired")
    for name in ("iat", "nbf"):
        if claims.get(name) is not None and claims[name] > moment + skew:
            raise InvalidTokenError(f"the token's '{name}' is in the future")


def verify_id_token(
    token: str, signing_key: KeyLookup, issuer: str, client_id: str, nonce: str, now: datetime
) -> Claims:
    """The ID token's claims, once it passes every check OpenID Connect Core 1.0 (3.1.3.7) asks of a client.

    Signature, issuer, audience (this client among them), times, `azp` (this client, if there are several audiences
    or it's present at all), and the nonce this sign-in sent, which ties the token to it. Raises InvalidTokenError.
    """
    claims = decode_signed(token, signing_key, issuer, client_id, ID_TOKEN_CLAIMS)
    check_times(claims, now)
    audiences = [claims["aud"]] if isinstance(claims["aud"], str) else claims["aud"]
    azp = claims.get("azp")
    if azp is not None and azp != client_id:
        raise InvalidTokenError("the token was issued to another client (azp)")
    if azp is None and len(audiences) > 1:
        raise InvalidTokenError("a token for several audiences must say which client it's for (azp)")
    sent = claims.get("nonce")
    if not isinstance(sent, str) or not hmac.compare_digest(sent.encode(), nonce.encode()):
        raise InvalidTokenError("the token's nonce isn't this sign-in's")
    return claims


def verify_logout_token(token: str, signing_key: KeyLookup, issuer: str, client_id: str, now: datetime) -> Claims:
    """The logout token's claims, once it passes the checks of Back-Channel Logout 1.0 (2.6).

    Signed by the provider for this client, the logout event present, a `sub` or a `sid` (or both), and no nonce
    (which would make it usable as an ID token). Raises InvalidTokenError.
    """
    claims = decode_signed(token, signing_key, issuer, client_id, LOGOUT_TOKEN_CLAIMS)
    check_times(claims, now)
    events = claims["events"]
    if not isinstance(events, dict) or not isinstance(events.get(BACKCHANNEL_LOGOUT_EVENT), dict):
        raise InvalidTokenError("the token doesn't announce a back-channel logout")
    if "nonce" in claims:
        raise InvalidTokenError("a logout token must not carry a nonce")
    if not isinstance(claims.get("sub"), str) and not isinstance(claims.get("sid"), str):
        raise InvalidTokenError("the logout token names neither a user (sub) nor a session (sid)")
    return claims


def roles_from(claims: Claims, claim: str) -> frozenset[str]:
    """The role names in `claim`: a claim of that exact name, else a dotted path (`realm_access.roles`).

    Providers shape it differently: a list of names, an object whose keys are the names, or a list of such
    objects (docs/identity_provider.md has each provider's). Anything else gives no roles.
    """
    value: Any = claims.get(claim)
    if value is None and "." in claim:
        value = claims
        for part in claim.split("."):
            value = value.get(part) if isinstance(value, dict) else None
    return frozenset(_role_names(value))


def _role_names(value: Any) -> set[str]:
    """The role names in one claim value (a name, a list, or an object keyed by name)."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return {key for key in value if isinstance(key, str)}
    if isinstance(value, list):
        return {name for item in value for name in _role_names(item)}
    return set()
