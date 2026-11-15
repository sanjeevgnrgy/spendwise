"""OidcIdentityProvider: the IdentityProvider port (core/identity.py) as standard OpenID Connect (infrastructure).

The one sign-in adapter. It speaks only the published standards: Discovery, the authorization code flow with PKCE
(RFC 7636, S256), the ID token's checks (Core 1.0), UserInfo, RP-Initiated Logout and Back-Channel Logout. So any
provider that implements them works by configuration alone (D185): its issuer URL, this app's client id and secret,
and, as data, its way of skipping to one login option and where it puts roles. The composition root builds it from
the OIDC_* settings; documents.py, exchange.py and tokens.py do the protocol's parts.
"""

import base64
import hashlib
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx2

from app.core.clock import Clock
from app.core.identity import IdentityError, LoginOption, LogoutNotice, VerifiedLogin
from app.infrastructure.identity.documents import ProviderDocuments
from app.infrastructure.identity.exchange import ClientCredentials, exchange_code, profile_claims
from app.infrastructure.identity.options import OidcLoginOption
from app.infrastructure.identity.tokens import roles_from, verify_id_token, verify_logout_token

# How long one request to the provider may take, connecting included. Sign-in waits for it.
HTTP_TIMEOUT_SECONDS = 10.0
RESPONSE_TYPE_CODE = "code"
# PKCE's challenge method: the SHA-256 of the verifier (RFC 7636, 4.2); "plain" would send the verifier itself.
CODE_CHALLENGE_METHOD = "S256"


def pkce_challenge(verifier: str) -> str:
    """The S256 code challenge for `verifier`: BASE64URL(SHA-256(verifier)), without padding (RFC 7636, 4.2)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def with_query(url: str, params: dict[str, str]) -> str:
    """`url` with `params` added to its query string (it may already have one)."""
    separator = "&" if urlsplit(url).query else "?"
    return url + separator + urlencode(params)


def _text(value: Any) -> str | None:
    """`value` if it's a non-empty string, else None: claims are only trusted to be what they say they are."""
    return value if isinstance(value, str) and value.strip() else None


def _display_name(profile: dict[str, Any]) -> str | None:
    """The name to show: `name`, else given and family names, else `preferred_username`."""
    parts = (_text(profile.get("given_name")), _text(profile.get("family_name")))
    given_family = " ".join(part for part in parts if part)
    return _text(profile.get("name")) or _text(given_family) or _text(profile.get("preferred_username"))


class OidcIdentityProvider:
    """Signs people in at one OpenID Connect provider, as one confidential client (with a secret)."""

    def __init__(
        self,
        issuer: str,
        credentials: ClientCredentials,
        clock: Clock,
        *,
        scopes: Sequence[str],
        options: Sequence[OidcLoginOption] = (),
        role_claim: str | None = None,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        """A client of the provider at `issuer`. `options` are the sign-in page's buttons, `role_claim` where the
        tokens list the person's roles. `transport` replaces the network (a check passes httpx2.MockTransport).

        Raises ValueError if two options share a key. Nothing is fetched yet: the provider is first asked at sign-in.
        """
        keys = [option.key for option in options]
        if len(set(keys)) != len(keys):
            raise ValueError("OIDC_LOGIN_OPTIONS has two options with the same key")
        self.issuer: str | None = issuer
        self._issuer = issuer
        self._credentials = credentials
        self._clock = clock
        self._scopes = tuple(dict.fromkeys(scopes))
        self._options = {option.key: option for option in options}
        self._role_claim = role_claim
        self._http = httpx2.Client(transport=transport, timeout=HTTP_TIMEOUT_SECONDS)
        self._documents = ProviderDocuments(issuer, self._http, clock)

    def login_options(self) -> list[LoginOption]:
        """The configured buttons, in their configured order."""
        return [LoginOption(key=option.key, label=option.label) for option in self._options.values()]

    def authorization_url(
        self, redirect_uri: str, state: str, nonce: str, code_verifier: str, option: str | None
    ) -> str:
        """The provider's authorization endpoint with this sign-in's request. An unknown `option` adds nothing (the
        provider shows its own page). Raises IdentityError if the metadata can't be read."""
        endpoint = self._documents.metadata().authorization_endpoint
        chosen = self._options.get(option) if option else None
        scopes = dict.fromkeys([*self._scopes, *(chosen.extra_scopes if chosen else ())])
        params = {
            # The option's own parameters go first, so the flow's own (OidcLoginOption refuses them anyway) win.
            **(chosen.extra_params if chosen else {}),
            "response_type": RESPONSE_TYPE_CODE,
            "client_id": self._credentials.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(code_verifier),
            "code_challenge_method": CODE_CHALLENGE_METHOD,
        }
        return with_query(endpoint, params)

    def complete_login(self, code: str, redirect_uri: str, code_verifier: str, nonce: str) -> VerifiedLogin:
        """Exchange the code, check the ID token, read the profile. Raises InvalidTokenError or IdentityError."""
        metadata = self._documents.metadata()
        tokens = exchange_code(self._http, metadata, self._credentials, code, redirect_uri, code_verifier)
        id_token = tokens["id_token"]
        claims = verify_id_token(
            id_token, self._documents.signing_key, self._issuer, self._credentials.client_id, nonce, self._clock.now()
        )
        profile = profile_claims(self._http, metadata, claims, tokens.get("access_token"), self._role_claim)
        return VerifiedLogin(
            issuer=self._issuer,
            subject=claims["sub"],
            id_token=id_token,
            session_id=_text(claims.get("sid")),
            email=_text(profile.get("email")),
            # Some providers send "true" as a string; anything else isn't a verified email.
            email_verified=profile.get("email_verified") in (True, "true"),
            name=_display_name(profile),
            picture=_text(profile.get("picture")),
            roles=roles_from(profile, self._role_claim) if self._role_claim else frozenset(),
        )

    def end_session_url(self, id_token: str | None, post_logout_redirect_uri: str) -> str | None:
        """The provider's end_session_endpoint with the ID token as a hint (RP-Initiated Logout 1.0); None if it has
        none, or its metadata can't be read (then only our own session ends)."""
        try:
            endpoint = self._documents.metadata().end_session_endpoint
        except IdentityError:
            return None
        if endpoint is None:
            return None
        params = {"client_id": self._credentials.client_id, "post_logout_redirect_uri": post_logout_redirect_uri}
        if id_token:
            params["id_token_hint"] = id_token
        return with_query(endpoint, params)

    def read_logout_token(self, logout_token: str) -> LogoutNotice:
        """Check a back-channel logout token (tokens.verify_logout_token). Raises InvalidTokenError or IdentityError."""
        claims = verify_logout_token(
            logout_token, self._documents.signing_key, self._issuer, self._credentials.client_id, self._clock.now()
        )
        return LogoutNotice(issuer=self._issuer, subject=_text(claims.get("sub")), session_id=_text(claims.get("sid")))
