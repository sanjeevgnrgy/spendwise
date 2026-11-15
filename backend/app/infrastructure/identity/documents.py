"""What an OpenID Connect provider publishes about itself: its metadata (discovery) and its signing keys (JWKS).

Part of the OIDC adapter (infrastructure). oidc.py reads the endpoints from ProviderDocuments.metadata() and hands
signing_key to tokens.py, which checks every token against it. Both documents are fetched on first use (never at
import or startup), kept for a while, and the keys are fetched again when a token names one they don't have: a
provider rotates its keys by publishing the new one first.
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx2

from app.core.clock import Clock
from app.core.identity import IdentityError, InvalidTokenError

# OpenID Connect Discovery 1.0, section 4: the metadata lives at the issuer's URL plus this path.
DISCOVERY_PATH = "/.well-known/openid-configuration"
# How long the metadata is trusted before it's read again.
METADATA_TTL = timedelta(hours=1)
# How often an unknown key id may trigger a new fetch of the keys, so a stream of forged tokens can't make us
# hammer the provider.
KEYS_REFETCH_INTERVAL = timedelta(minutes=1)
# What a JSON Web Key used for signatures says ("use"), when it says anything.
SIGNATURE_USE = "sig"

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ProviderMetadata:
    """The parts of the provider's discovery document the sign-in flow uses."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None
    end_session_endpoint: str | None
    # How a confidential client may authenticate at the token endpoint (client_secret_basic, client_secret_post...).
    token_auth_methods: tuple[str, ...]


def fetch_json(http: httpx2.Client, method: str, url: str, **request: Any) -> JsonObject:
    """One request to the provider, answered with a JSON object. Raises IdentityError if it can't be reached, answers
    with another status than 200, or with anything but a JSON object (the details go only to the server log)."""
    try:
        response = http.request(method, url, **request)
    except httpx2.HTTPError as error:
        raise IdentityError(f"{method} {url} failed: {error!r}") from error
    if response.status_code != httpx2.codes.OK:
        raise IdentityError(f"{method} {url} answered {response.status_code}: {response.text[:300]}")
    try:
        data = response.json()
    except ValueError as error:
        raise IdentityError(f"{method} {url} didn't answer with JSON") from error
    if not isinstance(data, dict):
        raise IdentityError(f"{method} {url} didn't answer with a JSON object")
    return data


def _parse_metadata(data: JsonObject, issuer: str) -> ProviderMetadata:
    """The metadata from a discovery document. Raises IdentityError if it's for another issuer (Discovery 1.0, 4.3:
    it must match exactly) or lacks an endpoint the flow needs."""
    if data.get("issuer") != issuer:
        raise IdentityError(f"the discovery document is for issuer {data.get('issuer')!r}, not {issuer!r}")
    required = ("authorization_endpoint", "token_endpoint", "jwks_uri")
    if not all(isinstance(data.get(name), str) for name in required):
        raise IdentityError("the discovery document lacks the authorization, token or jwks endpoint")
    methods = data.get("token_endpoint_auth_methods_supported")
    return ProviderMetadata(
        issuer=issuer,
        authorization_endpoint=data["authorization_endpoint"],
        token_endpoint=data["token_endpoint"],
        jwks_uri=data["jwks_uri"],
        userinfo_endpoint=data.get("userinfo_endpoint") if isinstance(data.get("userinfo_endpoint"), str) else None,
        end_session_endpoint=(
            data.get("end_session_endpoint") if isinstance(data.get("end_session_endpoint"), str) else None
        ),
        token_auth_methods=tuple(m for m in methods if isinstance(m, str)) if isinstance(methods, list) else (),
    )


class ProviderDocuments:
    """The provider's metadata and signing keys, fetched when first needed and cached. Safe to share between
    threads (routes run in a worker pool): one lock guards the cache."""

    def __init__(self, issuer: str, http: httpx2.Client, clock: Clock) -> None:
        """Documents for `issuer`, read through `http`; `clock` says when the cached copies are too old."""
        self._issuer = issuer
        self._http = http
        self._clock = clock
        self._lock = threading.Lock()
        self._metadata: ProviderMetadata | None = None
        self._metadata_at: datetime | None = None
        self._keys: dict[str, JsonObject] = {}
        self._keys_at: datetime | None = None

    def metadata(self) -> ProviderMetadata:
        """The provider's metadata, read again once METADATA_TTL has passed. Raises IdentityError."""
        with self._lock:
            now = self._clock.now()
            if self._metadata is None or self._metadata_at is None or now - self._metadata_at >= METADATA_TTL:
                url = self._issuer.rstrip("/") + DISCOVERY_PATH
                self._metadata = _parse_metadata(fetch_json(self._http, "GET", url), self._issuer)
                self._metadata_at = now
            return self._metadata

    def signing_key(self, key_id: str | None) -> JsonObject:
        """The signing key (a JSON Web Key) a token names in its header, fetching the keys again if it's unknown.

        Raises InvalidTokenError if the provider doesn't publish it, IdentityError if the keys can't be read.
        """
        metadata = self.metadata()
        with self._lock:
            key = self._find(key_id)
            if key is None and self._may_refetch():
                self._keys = self._fetch_keys(metadata.jwks_uri)
                self._keys_at = self._clock.now()
                key = self._find(key_id)
        if key is None:
            raise InvalidTokenError(f"the provider publishes no signing key {key_id!r}")
        return key

    def _may_refetch(self) -> bool:
        """Whether the keys may be fetched again now: never fetched, or not within KEYS_REFETCH_INTERVAL."""
        return self._keys_at is None or self._clock.now() - self._keys_at >= KEYS_REFETCH_INTERVAL

    def _find(self, key_id: str | None) -> JsonObject | None:
        """The cached key with `key_id`; with no id, the only key, if there's exactly one."""
        if key_id is None:
            return next(iter(self._keys.values())) if len(self._keys) == 1 else None
        return self._keys.get(key_id)

    def _fetch_keys(self, jwks_uri: str) -> dict[str, JsonObject]:
        """The provider's signing keys by key id (a key with no id is kept under ""). Raises IdentityError."""
        keys = fetch_json(self._http, "GET", jwks_uri).get("keys")
        if not isinstance(keys, list):
            raise IdentityError("the provider's JWKS has no 'keys' list")
        usable = [key for key in keys if isinstance(key, dict) and key.get("use", SIGNATURE_USE) == SIGNATURE_USE]
        return {str(key.get("kid", "")): key for key in usable}
