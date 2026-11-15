"""Talking to the provider's token and UserInfo endpoints, and reading a profile from what they say.

Part of the OIDC adapter (infrastructure); oidc.py calls exchange_code after the browser comes back with a code, then
profile_claims for the person's profile. Network failures are IdentityErrors; a UserInfo answer about anyone but the
person the ID token names is an InvalidTokenError.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import httpx2

from app.core.identity import IdentityError, InvalidTokenError
from app.infrastructure.identity.documents import JsonObject, ProviderMetadata, fetch_json

# How a confidential client authenticates at the token endpoint (OpenID Connect Core 1.0, 9). Basic is the default
# when the provider doesn't say (RFC 8414, 2).
CLIENT_SECRET_BASIC = "client_secret_basic"
CLIENT_SECRET_POST = "client_secret_post"
AUTHORIZATION_CODE = "authorization_code"
BEARER = "bearer"
# The profile claims the sign-in keeps. When the ID token lacks them (a provider may put them only in UserInfo for
# the code flow, as some do by default), UserInfo is asked.
PROFILE_CLAIMS = ("email", "name")


@dataclass(frozen=True)
class ClientCredentials:
    """This app's registration at the provider: its client id and secret (never sent to the browser)."""

    client_id: str
    client_secret: str


def _authentication(
    methods: tuple[str, ...], client: ClientCredentials
) -> tuple[dict[str, str], httpx2.BasicAuth | None]:
    """The form fields and Basic credentials that authenticate this client, by the methods the provider supports.

    Basic credentials are form-encoded first, as RFC 6749 (2.3.1) asks, so an id like `123@project` survives.
    Raises IdentityError if the provider supports neither secret-based method.
    """
    if not methods or CLIENT_SECRET_BASIC in methods:
        return {}, httpx2.BasicAuth(quote_plus(client.client_id), quote_plus(client.client_secret))
    if CLIENT_SECRET_POST in methods:
        return {"client_id": client.client_id, "client_secret": client.client_secret}, None
    raise IdentityError(f"the token endpoint supports none of our client authentication methods: {methods}")


def exchange_code(
    http: httpx2.Client,
    metadata: ProviderMetadata,
    client: ClientCredentials,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> JsonObject:
    """Trade the authorization code for tokens: POST to the token endpoint with the PKCE verifier.

    Returns the token response; it has an `id_token`. Raises IdentityError if the provider refuses or can't be
    reached (an expired or reused code included: the provider's words go to the server log).
    """
    fields, auth = _authentication(metadata.token_auth_methods, client)
    form = {
        "grant_type": AUTHORIZATION_CODE,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        **fields,
    }
    tokens = fetch_json(http, "POST", metadata.token_endpoint, data=form, auth=auth)
    if not isinstance(tokens.get("id_token"), str):
        raise IdentityError("the token response has no id_token")
    if "access_token" in tokens and str(tokens.get("token_type", "")).lower() != BEARER:
        raise IdentityError(f"unexpected token type {tokens.get('token_type')!r}")
    return tokens


def profile_claims(
    http: httpx2.Client,
    metadata: ProviderMetadata,
    id_claims: JsonObject,
    access_token: Any,
    role_claim: str | None = None,
) -> JsonObject:
    """The person's claims: the ID token's, completed from UserInfo when it lacks PROFILE_CLAIMS or `role_claim` (a
    provider may put the roles only in UserInfo; a role check would then refuse everyone).

    The ID token's own values win (they're signed). UserInfo's `sub` must be the ID token's (OpenID Connect Core 1.0,
    5.3.4), or the answer is about someone else: InvalidTokenError. Raises IdentityError if UserInfo can't be read.
    """
    missing = any(name not in id_claims for name in PROFILE_CLAIMS)
    if role_claim:
        # A dotted role claim (realm_access.roles) is there when its first part is.
        missing = missing or (role_claim not in id_claims and role_claim.split(".")[0] not in id_claims)
    if not missing or metadata.userinfo_endpoint is None or not isinstance(access_token, str):
        return id_claims
    headers = {"Authorization": f"Bearer {access_token}"}
    userinfo = fetch_json(http, "GET", metadata.userinfo_endpoint, headers=headers)
    if userinfo.get("sub") != id_claims.get("sub"):
        raise InvalidTokenError("UserInfo answered about another subject")
    return {**userinfo, **id_claims}
